# Investment pipeline teams
from .allocation_team import allocation_team
from .challenge_team import challenge_team
from .investment_committee_team import investment_committee_team
from .pipeline_team import pipeline_team
from .research_team import research_team


ALL_TEAMS = [
    research_team,
    challenge_team,
    allocation_team,
    investment_committee_team,
    pipeline_team,
]
