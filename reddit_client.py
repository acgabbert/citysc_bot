from typing import Optional, Union, Any
import asyncio
import logging
import asyncpraw, asyncpraw.models, asyncprawcore.exceptions

import config
import discord as msg

logger = logging.getLogger(__name__)

def subreddit_name(subreddit: str) -> str:
    """Strip a leading /r/ so '/r/stlouiscitysc' and 'stlouiscitysc' both work."""
    if '/r/' in subreddit:
        return subreddit.split('/r/')[1]
    return subreddit

# Errors worth retrying: 5xx and 429...
RETRYABLE_ERRORS = (
    asyncprawcore.exceptions.ServerError,
    asyncprawcore.exceptions.TooManyRequests,
)
# ...plus network failures (aiohttp connection errors and timeouts), but only for
# operations that are safe to repeat: a timed-out submit may have gone through.
RETRYABLE_ERRORS_IDEMPOTENT = RETRYABLE_ERRORS + (asyncprawcore.exceptions.RequestException,)

class RedditAPIError(Exception):
    """Base exception for Reddit API errors"""
    pass

class RedditClientError(RedditAPIError):
    """Client-side errors (4xx)"""
    pass

class RedditServerError(RedditAPIError):
    """Server-side errors (5xx)"""
    pass

class RedditClient:
    def __init__(self):
        self._client: Optional[asyncpraw.Reddit] = None
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.reddit_processing_delay = 10  # seconds after submissions/edits
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    @property
    def client(self) -> asyncpraw.Reddit:
        """Get the underlying Reddit client, connecting if necessary."""
        if not self._client:
            raise RedditClientError("Client not connected. Call connect() first.")
        return self._client

    async def connect(self) -> None:
        """Initialize the Reddit client connection."""
        if self._client:
            await self.close()
            
        self._client = asyncpraw.Reddit(
            client_id=config.CLIENT_ID,
            client_secret=config.SECRET_TOKEN,
            password=config.PASSWORD,
            user_agent=config.USER_AGENT_STR,
            username=config.USERNAME
        )
        self._client.validate_on_submit = True

    async def close(self) -> None:
        """Close the Reddit client connection."""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
            self._client = None

    async def refresh(self) -> None:
        """Refresh the Reddit client connection."""
        await self.close()
        await self.connect()

    async def _execute_with_retry(self, operation, *args, idempotent: bool = True, **kwargs) -> Any:
        """Execute a Reddit API operation, retrying server errors and rate limits
        (and network errors, if idempotent) with exponential backoff."""
        retryable = RETRYABLE_ERRORS_IDEMPOTENT if idempotent else RETRYABLE_ERRORS
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)

            except retryable as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    break

                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Reddit {type(e).__name__}, retrying in {wait_time}s: {str(e)}")
                # Don't refresh the client here: operation is bound to an object
                # (e.g. a Submission) that holds the current client's session.
                await asyncio.sleep(wait_time)

            except Exception as e:
                raise RedditClientError(f"Reddit operation failed: {str(e)}") from e

        raise RedditServerError(f"Operation failed after {self.max_retries} attempts: {str(last_error)}")

    async def submit_thread(
        self,
        subreddit: str,
        title: str,
        text: str,
        *,
        mod: bool = False,
        new: bool = False,
        unsticky: Optional[Union[str, asyncpraw.models.Submission]] = None
    ) -> asyncpraw.models.Submission:
        """Submit a new thread to Reddit."""
        subreddit = subreddit_name(subreddit)
            
        subreddit_obj = await self.client.subreddit(subreddit)
        
        # Submit the thread
        thread = await self._execute_with_retry(
            subreddit_obj.submit,
            idempotent=False,
            title=title,
            selftext=text,
            send_replies=False
        )
        
        if mod:
            await asyncio.sleep(self.reddit_processing_delay)
            if new:
                try:
                    await self._execute_with_retry(
                        thread.mod.suggested_sort,
                        sort='new'
                    )
                except Exception as e:
                    logger.error(f"Failed to set suggested sort for thread {thread.id}: {str(e)}")

            try:
                # Unsticky the old thread before stickying the new one so the new
                # thread takes the freed slot. Doing both at once can bump an
                # unrelated pinned post out of the bottom slot.
                if unsticky:
                    if isinstance(unsticky, str):
                        unsticky = await self.client.submission(id=unsticky)
                    try:
                        await self._execute_with_retry(
                            unsticky.mod.sticky,
                            state=False
                        )
                    except Exception as e:
                        logger.error(f"Failed to unsticky thread {unsticky.id}: {str(e)}")

                await self._execute_with_retry(
                    thread.mod.sticky
                )
            except Exception as e:
                logger.error(f"Moderation actions failed for thread {thread.id}: {str(e)}")
                msg.send("Warning: Moderation actions failed for new thread")
                
        return thread

    async def edit_thread(
        self,
        thread: Union[str, asyncpraw.models.Submission],
        text: str
    ) -> None:
        """Edit an existing thread."""
        if isinstance(thread, str):
            thread = await self.client.submission(id=thread)
            
        await self._execute_with_retry(thread.edit, text)
        await asyncio.sleep(self.reddit_processing_delay)

    async def add_comment(
        self,
        thread: Union[str, asyncpraw.models.Submission],
        text: str,
        *,
        distinguish: bool = False,
        sticky: bool = False
    ) -> Optional[asyncpraw.models.Comment]:
        """Add a comment to a thread."""
        if isinstance(thread, str):
            thread = await self.client.submission(id=thread)
            
        comment = await self._execute_with_retry(thread.reply, text, idempotent=False)
        
        if distinguish or sticky:
            await asyncio.sleep(self.reddit_processing_delay)
            try:
                await self._execute_with_retry(
                    comment.mod.distinguish,
                    sticky=sticky
                )
            except Exception as e:
                logger.error(f"Failed to distinguish comment {comment.id}: {str(e)}")
                
        return comment

    async def get_thread(
        self, 
        thread_id: str
    ) -> asyncpraw.models.Submission:
        """Get a Reddit thread by ID."""
        return await self.client.submission(id=thread_id)
    
    async def get_widgets(
        self,
        subreddit: str
    ) -> asyncpraw.models.SubredditWidgets:
        """Get a list of the widgets in a subreddit's sidebar"""
        subreddit = subreddit_name(subreddit)
        sub = await self.client.subreddit(subreddit)
        return sub.widgets


    async def get_image_data(
        self,
        widget: asyncpraw.models.SubredditWidgets,
        image_path: str,
        size: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """Update an image widget with an uploaded image"""
        image_url = await widget.mod.upload_image(image_path)
        image_data = [{'width': size[0], 'height': size[1], 'url': image_url, 'linkUrl': ''}]
        return image_data
    
    async def update_image_widget(
        self,
        widget_name: str,
        image_path: str,
        image_size: tuple[int, int],
        subreddit: str
    ) -> bool:
        """Update a subreddit's image widget"""
        subreddit = subreddit_name(subreddit)
        widgets = await self.get_widgets(subreddit)
        updated = False
        async for w in widgets.sidebar():
            logger.debug(w.shortName)
            if w.shortName == widget_name:
                try:
                    mod: asyncpraw.models.WidgetModeration = w.mod
                    image_data = await self.get_image_data(widgets, image_path, image_size)
                    await mod.update(data=image_data)
                    updated = True
                    msg.send(f'Updated {widget_name} widget on subreddit {subreddit}!')
                    break
                except Exception as e:
                    message = (
                        f'Error while updating {widget_name} widget.\n'
                        f'{str(e)}\n'
                    )
                    msg.send(message, tag=True)
        if not updated:
            msg.send(f'No widgets matching name "{widget_name}" on subreddit "{subreddit}" updated.', tag=True)
        return updated