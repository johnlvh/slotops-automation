# SlotOps Validation Rules

## RULE-001

field: minBet
severity: ERROR
condition: minBet must be greater than 0

## RULE-002

field: maxBet
severity: ERROR
condition: maxBet must be greater than minBet

## RULE-003

field: jackpot.value
severity: WARNING
condition: jackpot.value must not exceed 1000000

## RULE-004

field: campaign.start
severity: ERROR
condition: campaign.start must be earlier than campaign.end

## RULE-005

field: campaign.enabled
severity: ERROR
condition: disabled game must not have an active campaign

## RULE-006

field: jackpot.value
severity: WARNING
condition: jackpot.value must be 0 when jackpot is disabled

## RULE-007

field: campaign.end
severity: WARNING
condition: campaign.end must be in the future

## RULE-008

field: gameId
severity: ERROR
condition: gameId must not be empty

## RULE-009

field: featureFlags
severity: WARNING
condition: feature flags must be in approved list

## RULE-010

field: rewards
severity: ERROR
condition: reward IDs must be unique
