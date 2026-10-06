"""Realistic, reproducible sample content; never overwrite an existing account."""

import secrets
from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models import Summary, User
from app.models.user import utcnow
from app.services.summarizer import extractive_summary, word_count

SAMPLE_ARTICLES = [
    (
        "The next chapter of renewable energy",
        "Energy systems around the world are changing as communities invest in cleaner sources of electricity. Solar panels and wind turbines are becoming more affordable, helping local governments reduce dependence on fossil fuels. However, producing clean energy is only one part of the transition. Electricity must also be available when the sun is not shining and the wind is calm. Battery storage gives grid operators a way to save surplus power during periods of high production and release it when demand rises. Researchers are developing new battery materials that rely on abundant resources and can last through thousands of charging cycles. Public investment in transmission lines is equally important because renewable energy is often produced far from the cities that need it. Community energy projects allow residents to share the benefits of local installations and participate in decisions about their development. A successful transition combines technology, reliable infrastructure, and policies that make electricity accessible to everyone. Training programs can help workers gain skills in installation, maintenance, and grid management. Together, these efforts create an energy system that is more resilient, more efficient, and better prepared for the future.",
    ),
    (
        "Designing cities around people",
        "Urban planners are rethinking how streets, public spaces, and housing can support healthier daily lives. For decades, many cities prioritized moving cars quickly, often leaving pedestrians with narrow sidewalks and few safe crossings. A people-centered approach starts with the needs of residents who walk, cycle, or use public transportation. Wider sidewalks, protected bike lanes, and reliable bus services can make everyday journeys safer and more convenient. Trees and shaded seating help public spaces remain comfortable during warm weather. Mixed-use neighborhoods bring homes closer to shops, schools, and essential services, reducing the need for long trips. These improvements are most effective when communities are involved early in the planning process. Residents can identify barriers that are easy to overlook, such as inaccessible intersections or bus stops that lack shelter. Careful measurement helps cities understand whether changes are working. Planners can track travel times, traffic injuries, local business activity, and access to green space. Small pilot projects give neighborhoods a chance to test new ideas before larger investments are made. The goal is a city where more people have meaningful choices about how to travel and where public space supports connection, safety, and opportunity.",
    ),
    (
        "A practical guide to focused work",
        "Knowledge workers often face a steady stream of notifications, meetings, and changing priorities. These interruptions can make it difficult to complete tasks that require sustained attention. Focused work begins with choosing one important outcome and setting aside a realistic block of time to pursue it. Turning off nonessential notifications reduces the temptation to switch between applications. Writing down distracting thoughts allows a person to return to them later without losing the current train of thought. Teams can support focus by agreeing on when immediate responses are necessary and when asynchronous communication is sufficient. Meetings work better when they have a clear purpose, a short agenda, and a defined decision to make. Breaks are also part of a productive routine. A brief walk or a few minutes away from the screen can restore attention and help a person approach a difficult problem with fresh perspective. At the end of the day, reviewing what was completed makes progress visible and helps identify a useful starting point for tomorrow. Sustainable productivity is less about filling every minute and more about protecting attention for work that matters.",
    ),
    (
        "Responsible machine learning in practice",
        "Machine learning systems are increasingly used to help people organize information, recognize patterns, and make decisions. Building a useful model requires more than a high score on a benchmark. Developers need to understand where the training data came from, who is represented in it, and which situations the model may handle poorly. Clear documentation helps users understand what a system can reasonably do. Evaluation should include realistic examples from the environment where the model will be used. A model that performs well in a controlled test may behave differently when inputs contain unusual formatting, unfamiliar terminology, or missing context. Human review is valuable when the consequences of an error are significant. Teams should create ways to report problems, monitor changes in performance, and update a system when its assumptions no longer hold. Privacy also deserves attention throughout the development process. Collecting only necessary data and setting clear retention rules can reduce exposure. Responsible machine learning combines technical testing with careful product design. The result is a system that supports human judgment while making its limits visible.",
    ),
    (
        "Restoring coastal ecosystems",
        "Coastal ecosystems protect communities while supporting a remarkable variety of wildlife. Mangrove forests, salt marshes, and seagrass meadows absorb wave energy and provide nurseries for fish. They also store carbon in vegetation and waterlogged soil. Development, pollution, and rising sea levels have placed many of these habitats under pressure. Restoration projects begin by understanding why an ecosystem was damaged. Planting new vegetation may fail if tidal flows have been blocked or water quality remains poor. Scientists and local residents can work together to restore natural water movement and select appropriate native species. Long-term monitoring is essential because ecosystem recovery takes time. Researchers track plant survival, sediment changes, biodiversity, and the return of fish populations. Local communities often bring knowledge about seasonal conditions and historical changes that cannot be found in a short field survey. Supporting sustainable fishing and responsible tourism can create economic reasons to protect restored habitats. Effective conservation connects ecological goals with the needs of the people who depend on the coast. With consistent care, these landscapes can become living infrastructure for a more resilient future.",
    ),
    (
        "Learning that lasts beyond the classroom",
        "Students retain knowledge more effectively when they actively work with ideas instead of simply rereading notes. Retrieval practice encourages learners to recall information from memory, revealing what they understand and where they need more support. Spacing study sessions across several days gives the brain repeated opportunities to strengthen those connections. Explaining a concept in plain language can expose gaps that are hidden by familiar terminology. Teachers can support these habits with short quizzes, thoughtful feedback, and opportunities to apply concepts in new situations. A supportive classroom treats mistakes as useful evidence about the learning process. Students are more likely to ask questions when they feel that uncertainty is welcome. Clear goals help learners decide what to practice and recognize their progress. Rest and physical activity also influence attention and memory, so effective learning plans leave room for healthy routines. Technology can help organize materials and provide practice, but it works best when paired with purposeful instruction. The aim is to develop understanding that remains useful after an exam and builds confidence for future learning.",
    ),
]


def seed_database():
    if current_app.config["ENVIRONMENT"] == "production":
        raise RuntimeError("Demo seeding is disabled in production.")
    db.create_all()
    accounts = [
        ("admin", "admin@example.com", "Admin123!", True),
        ("demo", "demo@example.com", "Demo123!", False),
    ]
    accounts += [
        (name, f"{name}@example.com", secrets.token_urlsafe(24), False)
        for name in ("maya_chen", "oliver_reed", "sarah_kim", "james_wilson", "ava_patel")
    ]
    created_users, created_summaries = 0, 0
    users = []
    now = utcnow()
    for index, (username, email, password, is_admin) in enumerate(accounts):
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is None:
            if db.session.scalar(db.select(User).where(User.email == email)):
                raise RuntimeError(f"Seed email {email} already belongs to a different account.")
            user = User(
                username=username,
                email=email,
                is_admin=is_admin,
                created_at=now - timedelta(days=35 - index * 3),
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            created_users += 1
        users.append(user)
    for index in range(21):
        key = f"portfolio-demo-{index + 1:02}"
        if db.session.scalar(db.select(Summary.id).where(Summary.seed_key == key)):
            continue
        title, text = SAMPLE_ARTICLES[index % len(SAMPLE_ARTICLES)]
        length = ("short", "medium", "long")[index % 3]
        summary = extractive_summary(text, length)
        original_words, summary_words = word_count(text), word_count(summary)
        # Keep examples visibly varied across the seven-day analytics window.
        owner = users[1] if index % 4 == 0 else users[index % len(users)]
        db.session.add(
            Summary(
                user_id=owner.id,
                title=title,
                original_text=text,
                summarized_text=summary,
                summary_length=length,
                original_word_count=original_words,
                summary_word_count=summary_words,
                compression_ratio=round((1 - summary_words / original_words) * 100, 1),
                processing_time=round(0.012 + index * 0.003, 3),
                method="extractive",
                created_at=now - timedelta(days=index % 7, minutes=index * 13),
                seed_key=key,
            )
        )
        created_summaries += 1
    db.session.commit()
    return f"Demo data ready: added {created_users} users and {created_summaries} summaries. Existing accounts were preserved."
