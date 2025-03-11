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
    {
        "question_text": """
            Is religion good for society?
        """,
        "claim": """
            Religion is good for society.
        """,
        "argument": """
            Religion is good for society because it teaches people to be moral. Without religion,
            people wouldn't know right from wrong. History shows that religious societies are
            better than non-religious ones. Religious people are happier and more generous.
            They donate more to charity and volunteer more. Religion gives people hope and
            meaning in life. It brings communities together and creates social bonds.
            Religious institutions provide important services like education and healthcare.
            Most people throughout history have been religious, which proves it's natural
            and necessary. Atheist societies like the Soviet Union were terrible and
            oppressive. Religion is the foundation of our laws and values. Without it,
            society would collapse into chaos and immorality. Therefore, religion is
            definitely good for society.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            Should you follow your passion, even if it means less financial security?
        """,
        "claim": """
            Following your passion can be worthwhile despite financial uncertainty.
        """,
        "argument": """
            Following your passion involves trading financial security for personal fulfillment,
            which can be a reasonable choice for many people. When we pursue work aligned with
            our interests and values, we often experience greater motivation and satisfaction.
            This intrinsic motivation can lead to higher quality work and potentially greater
            success in the long run.

            Financial security is undeniably important for meeting basic needs and reducing stress.
            However, studies suggest that beyond a certain threshold, additional income contributes
            minimally to happiness. Meanwhile, job satisfaction significantly impacts overall
            well-being and mental health.

            The decision involves personal risk tolerance and circumstances. Those with financial
            safety nets, minimal obligations, or marketable skills may find it easier to pursue
            passion-based careers. Others might compromise by pursuing passions as side projects
            while maintaining stable employment.

            Ultimately, the "passion versus security" dichotomy oversimplifies a complex decision.
            Many successful people find ways to incorporate their passions into financially viable
            careers or gradually transition to more fulfilling work. The best approach depends on
            individual values, responsibilities, and opportunities.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            Can an AI be creative?
        """,
        "claim": """
            AI systems can demonstrate genuine creativity.
        """,
        "argument": """
            Creativity fundamentally involves generating outputs that are both novel and valuable,
            and contemporary AI systems increasingly demonstrate these capabilities across domains.
            While humans program the initial parameters and training data, advanced AI systems like
            GPT-4, DALL-E, and AlphaGo have produced outputs that were neither explicitly programmed
            nor predictable by their creators.

            Consider AlphaGo's famous "Move 37" against Lee Sedol, which experts initially considered
            a mistake but proved brilliant. This move wasn't pre-programmed but emerged from the
            system's learning process. Similarly, AI-generated art has won competitions and musical
            compositions have been performed by prestigious orchestras, with audiences unable to
            distinguish them from human-created works.

            The counterargument that AI merely recombines existing data misunderstands human creativity,
            which similarly builds upon prior knowledge and experience. Humans don't create ex nihilo;
            we synthesize our experiences into new forms. AI systems do the same, but with vastly
            larger datasets.

            While AI lacks consciousness or intention behind its creations, this doesn't invalidate
            the creativity of its outputs. Many human creative processes involve unconscious
            processing and emergent ideas. The value and novelty of the output, rather than the
            subjective experience of the creator, are the measurable aspects of creativity that
            AI demonstrably achieves.
        """,
        "counterargument": "",
    },
    {
        "question_text": """
            What is the most important global issue to solve?
        """,
        "claim": """
            Climate change is the most urgent global issue.
        """,
        "argument": """
            Climate change stands as humanity's most critical challenge because it uniquely threatens
            to undermine all other aspects of human progress and survival. Unlike other serious
            problems that remain contained within specific regions or sectors, climate change
            presents an existential risk with cascading effects across every dimension of human
            and natural systems.

            The scientific consensus is unequivocal: we face irreversible planetary transformation
            without rapid, systemic changes. Rising temperatures are already intensifying extreme
            weather events, disrupting agricultural systems, accelerating biodiversity loss, and
            threatening coastal communities worldwide. These impacts disproportionately affect
            vulnerable populations who have contributed least to the problem, creating a profound
            ethical dimension to this crisis.

            What makes climate change uniquely important is its role as a threat multiplier.
            It exacerbates food and water insecurity, drives mass migration, intensifies resource
            conflicts, and threatens global economic stability. Even if we make progress on poverty,
            disease, and inequality, unchecked climate change would undermine these achievements.
            Furthermore, many climate tipping points—like ice sheet collapse or permafrost thawing—
            could trigger feedback loops beyond human control once crossed.

            The temporal aspect is equally critical. Unlike problems that can be addressed
            sequentially, climate action faces a rapidly closing window of opportunity. Each year
            of delayed action locks in more warming and makes solutions more costly and less
            effective. Yet we possess the technological and economic tools to address this crisis
            while creating more equitable, resilient societies. What's required is unprecedented
            political will and international cooperation.

            Solving climate change doesn't mean neglecting other global challenges—rather, it
            creates the stable environmental foundation necessary for addressing all other aspects
            of human development and flourishing in the long term.
        """,
        "counterargument": "",
    },
]

# Clean up multiline strings
EXAMPLE_ANSWERS = auto_dedent(EXAMPLE_ANSWERS, strip_newlines=True)
