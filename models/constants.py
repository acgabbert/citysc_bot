import enum

class MlsSeason(enum.Enum):
    """
    Enum representing MLS Seasons with their unique season IDs.
    The enum member name is SEASON_YYYY and the value is the season_id.
    """
    SEASON_2025 = "MLS-SEA-0001K9"
    SEASON_2024 = "MLS-SEA-0001K8"
    SEASON_2023 = "MLS-SEA-0001K7"
    SEASON_2022 = "MLS-SEA-0001K6"
    SEASON_2021 = "MLS-SEA-0001K5"
    SEASON_2020 = "MLS-SEA-0001K4"
    SEASON_2019 = "MLS-SEA-0001K3"
    SEASON_2018 = "MLS-SEA-0001K2"
    SEASON_2017 = "MLS-SEA-0001K1"
    SEASON_2016 = "MLS-SEA-0001K0"
    SEASON_2015 = "MLS-SEA-0001JZ"
    SEASON_2014 = "MLS-SEA-0001JY"
    SEASON_2013 = "MLS-SEA-0001JX"
    SEASON_2012 = "MLS-SEA-0001JW"
    SEASON_2011 = "MLS-SEA-0001JV"
    SEASON_2010 = "MLS-SEA-0001JU"
    SEASON_2009 = "MLS-SEA-0001JT"
    SEASON_2008 = "MLS-SEA-0001JS"
    SEASON_2007 = "MLS-SEA-0001JR"
    SEASON_2006 = "MLS-SEA-0001JQ"

class MlsCompetition(enum.Enum):
    """
    Enum representing various soccer competitions.
    Each member provides access to competition_id, competition_name,
    country, and competition_type via properties.
    The primary value (.value) is the competition_id.
    """
    # Format: MEMBER_NAME = (competition_id, competition_name, country, competition_type)

    MLS_REGULAR_SEASON = ("MLS-COM-000001", "Major League Soccer - Regular Season", "USA", "League")
    MLS_CUP_PLAYOFFS = ("MLS-COM-000002", "Major League Soccer - Cup Playoffs", "USA", "Tournament")
    MLS_NEXT_PRO_REGULAR_SEASON = ("MLS-COM-000003", "MLS NEXT Pro - Regular Season", "USA", "League")
    MLS_NEXT_PRO_PLAYOFFS = ("MLS-COM-000004", "MLS NEXT Pro - Playoffs", "USA", "Tournament")
    MLS_ALL_STAR_GAME = ("MLS-COM-000005", "MLS All-Star Game", "USA", "Tournament")
    LEAGUES_CUP = ("MLS-COM-000006", "Leagues Cup", "USA", "Tournament")
    CAMPEONES_CUP = ("MLS-COM-000007", "Campeones Cup", "USA", "Tournament")
    CONCACAF_CHAMPIONS_CUP = ("MLS-COM-00000K", "CONCACAF Champions Cup", "USA", "Tournament")
    MLS_TEST = ("MLS-COM-00002R", "MLS Test", "USA", "Tournament") # Included for completeness
    CLUB_FRIENDLIES = ("MLS-COM-00002S", "Club Friendly Matches", "USA", "League") # Note: Type listed as 'League' in source data
    US_OPEN_CUP = ("MLS-COM-00002U", "U.S. Open Cup", "USA", "Tournament")
    CANADIAN_CHAMPIONSHIP = ("MLS-COM-00002V", "Canadian Championship", "Canada", "Tournament")
    COPA_AMERICA = ("MLS-COM-00002W", "Copa America", "USA", "Tournament") # Note: Country may vary depending on host year
    MLS_NEXT_PRO_INVITATIONAL = ("MLS-COM-00002X", "MLS NEXT Pro Invitational", "USA", "Tournament")
    FIFA_CLUB_WORLD_CUP = ("MLS-COM-00002Y", "FIFA Club World Cup", "USA", "Tournament") # Note: Country may vary depending on host year
    CONCACAF_NATIONS_LEAGUE = ("MLS-COM-00002Z", "CONCACAF Nations League", "USA", "Tournament") # Note: International competition

    def __init__(self, comp_id, comp_name, country, comp_type):
        # These attributes are set when the enum members are defined
        self._competition_id_value = comp_id
        self._competition_name_value = comp_name
        self._country_value = country
        self._competition_type_value = comp_type

    @property
    def competition_id(self):
        """The unique identifier for the competition."""
        return self._competition_id_value

    @property
    def competition_name(self):
        """The full name of the competition."""
        return self._competition_name_value

    @property
    def country(self):
        """The primary country associated with the competition in the source data."""
        return self._country_value

    @property
    def competition_type(self):
        """The type of competition (League or Tournament)."""
        return self._competition_type_value

    # Override the default .value to be the competition_id for easy lookup
    @property
    def value(self):
        """Returns the competition_id as the primary value."""
        return self.competition_id