from pydantic import BaseModel


class Item(BaseModel):
    freq_min: int
    src_lang: str
    tgt_lang: str
    src_texts: list[str]
    tgt_texts: list[str]


class Term(BaseModel):
    src_term: str
    tgt_term: str
    rank: float
    src_label: str
    src_frequency: int
    src_cluster: int
    origin: str
    frequency: int
    similarity: float


class Tm2tbTerms(BaseModel):
    terms: list[Term]


class SummaryInput(BaseModel):
    source_text: str


class Sentence(BaseModel):
    text: str
    rank_score: float
    offset: int
    length: int


class SummaryResponse(BaseModel):
    summary: list[Sentence]


class SuggestionTerm(BaseModel):
    lang: str
    text: str


class StartSessionResponse(BaseModel):
    message: str


class CloseSessionResponse(BaseModel):
    message: str
