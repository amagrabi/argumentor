from utils import auto_dedent

EXAMPLE_ANSWERS = [
    {
        "question_text": """
            In decision-making, is relying on the bandwagon effect a justifiable
            strategy when evidence is scarce, or is it a flawed approach that should
            be avoided at all costs?
        """,
        "claim": """
            Following the bandwagon effect is a justifiable strategy when evidence
            is scarce.
        """,
        "argument": """
            When evidence is scarce, you do not have a lot of reliable options to
            guide decision-making. Without evidence, you cannot put confidence in
            the truthfulness of any assumptions. And without a solid foundation,
            you cannot construct solid arguments. So in a situation when you have
            no evidence, it would be best to take more time and search evidence.
            But if you do not have that time and need to make a decision now, it
            can be better to follow the majority, because it has a higher likelihood
            of success.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            Should AI be permitted to autonomously make life-or-death decisions
            (e.g., in automated warfare) if it reduces human casualties?
        """,
        "claim": "AI should be permitted to make important life-or-death decisions.",
        "argument": """
            AI has demonstrated super-human intelligence on many domains already.
            If that is the case, then AI is capable of making better or equal decisions
            than humans. Therefore, AI should be permitted to make important life-or-death
            decisions, because there is a high chance that it outperforms humans and can
            save more lives in the long run.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            Can free will exist if our decisions are determined by biological and
            physical influences?
        """,
        "claim": """
            Free will can exist if our decisions are determined by biological and
            physical influences.
        """,
        "argument": """
            Free decisions are decisions that are aligned with and a consequence of
            our internal beliefs and goals. All our internal beliefs and goals are
            determined by biology/physics, because they are determined by our brain.
            Therefore, these influence are not 'bad', but actually a requirement for
            free will. The important part is that these influences result from
            cognitive processes that are aligned with our conscious beliefs and goals,
            instead of subconscious influences that go against them.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            Can free will exist if our decisions are determined by biological and
            physical influences?
        """,
        "claim": "Potatoes are good.",
        "argument": """
            Potatoes contain vitamins. Potatoes are organic. Therefore they are healthy.
            Also, potatoes taste good, and potatoes can be used in a variety of dishes.
            Therefore, potatoes are good.
        """,
        "counterargument": "",
    },
]

# Clean up multiline strings
EXAMPLE_ANSWERS = auto_dedent(EXAMPLE_ANSWERS, strip_newlines=True)
