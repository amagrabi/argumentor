from utils import auto_dedent

EXAMPLE_ANSWERS = [
    {
        "question_text": """
            What is more important, experiences or material possessions?
        """,
        "claim": """
            Material possessions are ultimately more important than experiences
            for long-term well-being and a fulfilling life.
        """,
        "argument": """
            While experiences are often lauded for their ability to create memories
            and personal growth, material possessions provide a more fundamental and
            lasting foundation for a good life. Experiences are ephemeral; they fade
            into memory, and their positive effects diminish over time. In contrast,
            well-chosen material possessions offer enduring benefits that contribute
            to stability, security, and continued well-being.

            Firstly, material possessions provide security and stability. Owning a home,
            for example, offers shelter and a sense of place, crucial for mental and
            emotional well-being. Financial assets, like savings and investments,
            provide a safety net against unforeseen circumstances such as job loss or
            medical emergencies. This security reduces stress and allows individuals
            to navigate life's challenges with greater confidence. Experiences, however
            enriching, do not offer this tangible security; the memories of a vacation
            cannot pay the rent during hard times.

            Secondly, many material possessions are inherently practical and functional,
            directly improving daily life. Reliable transportation, efficient appliances,
            and comfortable living spaces are not luxuries, but necessities that
            enhance our quality of life day in and day out. These possessions
            save time, reduce effort, and create a more comfortable and productive environment.
            While experiences can be enjoyable, they often require a foundation of material
            comfort to be fully appreciated. It's difficult to savor a travel experience when
            one is constantly worried about basic needs or lacks a comfortable home to return to.

            Thirdly, material possessions can create a lasting legacy and provide
            for future generations. Assets and heirlooms can be passed down, offering
            continued benefit and connection across time. This provides a sense of
            continuity and purpose that extends beyond one's own lifespan. Experiences,
            being personal and intangible, cannot be directly inherited in the same way.
            While stories and memories can be shared, the tangible benefits of experiences
            are not transferable to future generations.

            Finally, it's important to recognize that material possessions are not inherently opposed to experiences; they can often facilitate and enhance them. Having a car enables travel experiences, owning sports equipment allows for active and engaging hobbies, and a comfortable home provides a base for social gatherings and shared experiences. The key is to prioritize meaningful material possessions that contribute to long-term well-being and enable a richer life, rather than succumbing to mindless consumerism.
            In conclusion, while the fleeting joy of experiences is valuable, it is the enduring stability, practicality, and legacy provided by material possessions that ultimately contribute more significantly to a secure, comfortable, and fulfilling life, both for ourselves and for those who come after us.
        """,
        "counterargument": "",
    },
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
            Would the introduction of Ranked Choice Voting (RCV) strengthen democracy?
        """,
        "claim": "The introduction of Ranked Choice Voting (RCV) would strengthen democracy.",
        "argument": """
            Ranked Choice Voting (RCV) strengthens democracy by ensuring majority rule,
            reducing polarization, and expanding voter choice. Unlike first-past-the-post,
            where candidates can win with a mere plurality, RCV ensures winners have true
            majority support by redistributing votes until one candidate surpasses 50%.
            This eliminates the spoiler effect, allowing voters to rank their true preferences
            without fear of wasting their vote.

            RCV also reduces negative campaigning, as candidates must appeal to a broader
            audience to gain second-choice rankings. It encourages political diversity,
            weakening two-party dominance and giving independent candidates a fairer chance.
            Moreover, RCV increases voter engagement, as people feel their choices matter more.

            By making elections fairer, reducing strategic voting, and promoting consensus-driven
            leadership, RCV creates a stronger, more representative democracy.
        """,
        "counterargument": "",
    },
]

# Clean up multiline strings
EXAMPLE_ANSWERS = auto_dedent(EXAMPLE_ANSWERS, strip_newlines=True)
