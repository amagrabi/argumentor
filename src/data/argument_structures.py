ARGUMENT_STRUCTURE_LONG = {
    "nodes": [
        {
            "id": "p1",
            "type": "premise",
            "text": "Main premise: AI has demonstrated superhuman performance in multiple domains including chess, go, and medical diagnosis",
        },
        {
            "id": "p2",
            "type": "premise",
            "text": "Supporting premise: In controlled tests, AI systems make fewer errors than human experts when processing large amounts of data",
        },
        {
            "id": "p3",
            "type": "premise",
            "text": "Supporting premise: AI systems can process information faster and consider more variables simultaneously than humans",
        },
        {
            "id": "p4",
            "type": "premise",
            "text": "Intermediate conclusion: AI systems are capable of making more accurate decisions than humans in specific domains",
        },
        {
            "id": "p5",
            "type": "premise",
            "text": "Qualifying premise: When proper safety measures and human oversight are in place, AI systems can be reliably deployed",
        },
        {"id": "c1", "type": "conclusion", "text": "This is an example of a claim."},
    ],
    "edges": [
        {"from": "p1", "to": "p4"},
        {"from": "p2", "to": "p4"},
        {"from": "p3", "to": "p4"},
        {"from": "p4", "to": "c1"},
        {"from": "p5", "to": "c1"},
    ],
}

ARGUMENT_STRUCTURE_SHORT = {
    "nodes": [
        {
            "id": "p1",
            "type": "premise",
            "text": "Main premise: AI has demonstrated superhuman performance in multiple domains including chess, go, and medical diagnosis",
        },
        {
            "id": "p2",
            "type": "premise",
            "text": "Supporting premise: In controlled tests, AI systems make fewer errors than human experts when processing large amounts of data",
        },
        {"id": "c1", "type": "conclusion", "text": "This is an example of a claim."},
    ],
    "edges": [
        {"from": "p1", "to": "c1"},
        {"from": "p2", "to": "c1"},
    ],
}
