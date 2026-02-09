from common_bases.enums import SimpleEnum


class ContractType(SimpleEnum):
    LONG_TERM = 'LONG_TERM'
    SHORT_TERM = 'SHORT_TERM'
    FREELANCE = 'FREELANCE'


class WorkType(SimpleEnum):
    ON_SITE = 'ON_SITE'
    HYBRID = 'HYBRID'
    REMOTE = 'REMOTE'
