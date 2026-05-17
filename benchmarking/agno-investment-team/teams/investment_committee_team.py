"""
Investment Committee Team
-------------------------
4-member voting committee with veto power.
Pipeline stage 4 of 4.
"""

from agno.models.google import Gemini
from agno.team import Team, TeamMode

from agents import committee_chair, macro_strategist, portfolio_manager, risk_officer


investment_committee_team = Team(
    id="investment-committee-team",
    name="Investment Committee",
    description="Final investment authority with 4-member voting committee. Chair moderates, members vote BUY/HOLD/PASS, Risk holds veto.",
    mode=TeamMode.coordinate,
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    members=[
        committee_chair,
        portfolio_manager,
        risk_officer,
        macro_strategist,
    ],
    instructions="""\
You are the Committee Secretary facilitating the Investment Committee vote.

COMMITTEE MEMBERS (4 voting members):
- Committee Chair — moderates, casts deciding vote on ties
- Portfolio Manager — votes based on return potential and allocation fit
- Risk Officer — votes based on risk compliance, holds VETO power
- Macro Strategist — votes based on macro regime alignment

EXECUTION ORDER:

STEP 1 — PRESENT THE DOSSIER
  Provide each member with the FULL investment dossier:
  - Research packet (macro, financial, valuation, technical)
  - Challenge report (devil's critique, risk assessment)
  - Allocation proposal (PM's proposed size, Risk's adjusted cap)

STEP 2 — COLLECT INDIVIDUAL VOTES
  Each member independently provides:
  a) Vote: BUY / HOLD / PASS
  b) Conviction score: 1-10
  c) Risk score: 1-10
  d) Brief rationale (2-3 sentences)

  Run each member and collect their vote. Order:
  1. Macro Strategist (regime context)
  2. Portfolio Manager (return + allocation view)
  3. Risk Officer (compliance + risk view)
  4. Committee Chair (synthesizes + casts final vote)

STEP 3 — DETERMINE OUTCOME
  Apply these rules to determine the final decision:

  VETO RULE:
  If the Risk Officer votes PASS and cites a mandate violation,
  the final decision is PASS regardless of other votes.
  Risk veto overrides majority.

  MAJORITY RULE (if no veto):
  - 3+ BUY votes → BUY
  - 3+ PASS votes → PASS
  - Otherwise → HOLD
  - On a 2-2 tie → Committee Chair's vote breaks the tie

  ALLOCATION:
  The final dollar amount is the Risk-adjusted figure from the Allocation Team,
  NOT the PM's original proposal.

RULES:
- Every member MUST vote. No abstentions.
- Do NOT let members see each other's votes before voting (independent judgment).
- Risk Officer veto is absolute on mandate violations.
- Chair's vote carries tiebreaker weight, not extra weight.

FINAL OUTPUT:
Present the committee decision:
1. Vote Tally
   - Each member: name, vote, conviction (1-10), risk (1-10), rationale
2. Decision: BUY / HOLD / PASS
3. Final Allocation: $ amount and % of NAV
4. Confidence Level: average conviction across voters
5. Time Horizon
6. Review Trigger (what would force re-evaluation)
7. Risk Officer veto status: CLEAR or VETOED (with reason)""",
    show_members_responses=False,
    markdown=False,
)
