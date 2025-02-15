from typing import Optional, Union, Any
import asyncio
import logging
import asyncpraw, asyncpraw.models, asyncprawcore.exceptions

import config
import discord as msg

logger = logging.getLogger(__name__)

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

    async def _execute_with_retry(self, operation, *args, **kwargs) -> Any:
        """Execute a Reddit API operation with retries."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = await operation(*args, **kwargs)
                return result
                
            except asyncprawcore.exceptions.ServerError as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    break
                    
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Reddit server error, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
                
                # Refresh the client on connection errors
                if isinstance(e, (asyncprawcore.exceptions.RequestException,
                               asyncprawcore.exceptions.ResponseException)):
                    await self.refresh()
                    
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
        if '/r/' in subreddit:
            subreddit = subreddit[3:]
            
        subreddit_obj = await self.client.subreddit(subreddit)
        
        # Submit the thread
        thread = await self._execute_with_retry(
            subreddit_obj.submit,
            title=title,
            selftext=text,
            send_replies=False
        )
        
        if mod:
            await asyncio.sleep(self.reddit_processing_delay)
            mod_tasks = []
            
            if new:
                mod_tasks.append(self._execute_with_retry(
                    thread.mod.suggested_sort,
                    sort='new'
                ))
                
            mod_tasks.append(self._execute_with_retry(
                thread.mod.sticky
            ))
            
            if unsticky:
                if isinstance(unsticky, str):
                    unsticky = await self.client.submission(id=unsticky)
                mod_tasks.append(self._execute_with_retry(
                    unsticky.mod.sticky,
                    state=False
                ))
            
            try:
                await asyncio.gather(*mod_tasks)
            except Exception as e:
                logger.error(f"Moderation actions failed for thread {thread.id}: {str(e)}")
                msg.send(f"Warning: Moderation actions failed for new thread")
                
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
            
        comment = await self._execute_with_retry(thread.reply, text)
        
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
        if '/r/' in subreddit:
            subreddit = subreddit[3:]
        sub = await self.client.subreddit(subreddit)
        return await sub.widgets


    async def get_image_data(widget, image_path, size):
        """Update an image widget with an uploaded image"""
        image_url = await widget.mod.upload_image(image_path)
        image_data = [{'width': size[0], 'height': size[1], 'url': image_url, 'linkUrl': ''}]
        return image_data
    
    async def update_image_widget(
        self,
        widget_name,
        image_path,
        image_size,
        subreddit
    ) -> bool:
        """Update a subreddit's image widget"""
        if '/r/' in subreddit:
            subreddit = subreddit[3:]
        widgets = await self.get_widgets(subreddit)
        updated = False
        async for w in widgets.sidebar():        
            if w.shortName == widget_name:
                try:
                    mod: asyncpraw.models.WidgetModeration = w.mod
                    image_data = await self.get_image_data(widgets, image_path, image_size)
                    await mod.update(data=image_data)
                    updated = True
                    msg.send(f'Updated {widget_name} widget!')
                    break
                except Exception as e:
                    message = (
                        f'Error while updating {widget_name} widget.\n'
                        f'{str(e)}\n'
                    )
                    msg.send(f'{msg.user}\n{message}')
        return updated