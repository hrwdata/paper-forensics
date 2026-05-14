from paper_forensics.nlp.sentence_split import split_sentences


def test_sentence_split_handles_abbreviations_and_decimals() -> None:
    text = "We compare against e.g. prior work. The score is 3.14 in Fig. 2. This remains stable."
    sentences = split_sentences(text)
    assert sentences == [
        "We compare against e.g. prior work.",
        "The score is 3.14 in Fig. 2.",
        "This remains stable.",
    ]
