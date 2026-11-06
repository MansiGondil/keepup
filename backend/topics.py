"""The 13 Keepup topics, described in words so we can compare them with articles.

TOPIC_DESCRIPTIONS: one description per topic (variant A and B in eval_topics.py).
TOPIC_VARIANTS: three short descriptions per topic from different angles
(variant C): a definition, a list of typical keywords, and a typical headline.
Keys are the topic tags used in the API.
"""

TOPIC_DESCRIPTIONS = {
    "ai": "Artificial intelligence: AI models, chatbots, large language models, AI companies and products, AI agents, and AI safety, regulation and policy.",
    "data-ml": "Data and machine learning: data engineering, analytics, databases, datasets, benchmarks, machine learning methods, training and evaluating models, and ML research papers.",
    "sre": "Site reliability and operations: outages and incidents, postmortems, uptime, observability and monitoring, on-call, Kubernetes, cloud infrastructure, DevOps and system reliability.",
    "security": "Cybersecurity: vulnerabilities, security patches, data breaches, hacking, ransomware, cyber-attacks and online privacy incidents.",
    "business": "Business: companies, earnings, markets, mergers and deals, startups, industry news and the economy.",
    "politics": "Politics: government, elections, parliaments and Congress, political parties, politicians, laws and public policy.",
    "world": "World affairs: international relations, diplomacy, wars and conflicts, foreign countries, and global events.",
    "health": "Health: medicine, diseases, hospitals, public health, nutrition, fitness, mental health and medical research.",
    "money": "Personal finance: prices, interest rates, mortgages, taxes, savings, cost of living, wages and household budgets.",
    "science": "Science: scientific research, space, astronomy, physics, biology, climate and the environment.",
    "careers": "Careers: jobs, hiring, layoffs, the workplace, salaries, skills and professional development.",
    "sports": "Sports: football, soccer, basketball, tennis, cricket, athletes, matches, tournaments and results.",
    "entertainment": "Entertainment: films, television, music, celebrities, streaming, books and the arts.",
}

# Order inside each list: [definition, keywords, headline style].
TOPIC_VARIANTS = {
    "ai": [
        "News about artificial intelligence systems and the companies that build them.",
        "AI, LLM, chatbot, GPT, neural network, generative AI, AI agent, open-weight model, AI lab",
        "AI startup releases new language model that beats rivals on coding tasks",
    ],
    "data-ml": [
        "Work on data and machine learning: how data is stored and processed and how models are trained and evaluated.",
        "dataset, data pipeline, SQL, data warehouse, analytics, training, benchmark, classifier, regression, research paper",
        "Researchers propose a faster method for training models on large datasets",
    ],
    "sre": [
        "Keeping software services running: reliability, infrastructure and incident response.",
        "outage, downtime, incident, postmortem, Kubernetes, cloud, servers, monitoring, latency, deployment, on-call",
        "Cloud provider outage takes down websites for several hours",
    ],
    "security": [
        "Protecting computers, networks and data from attackers.",
        "vulnerability, CVE, exploit, malware, ransomware, breach, hackers, phishing, patch, zero-day",
        "Hackers exploit flaw to steal millions of customer records",
    ],
    "business": [
        "News about companies, industries, markets and the economy.",
        "company, earnings, revenue, profit, shares, stock market, acquisition, merger, CEO, startup, sales",
        "Company shares jump after quarterly profits beat expectations",
    ],
    "politics": [
        "News about governments, elections and the people and parties who run them.",
        "election, government, parliament, Congress, president, prime minister, party, vote, minister, bill, law",
        "Ruling party loses majority as voters turn against the government",
    ],
    "world": [
        "News about relations between countries and major events abroad.",
        "international, diplomacy, foreign minister, summit, sanctions, war, conflict, ceasefire, treaty, United Nations",
        "Leaders meet at summit as talks on ceasefire continue",
    ],
    "health": [
        "News about people's physical and mental health and medical care.",
        "health, doctors, hospital, NHS, disease, cancer, treatment, vaccine, symptoms, patients, mental health",
        "New blood test could help doctors spot cancer earlier",
    ],
    "money": [
        "News about household money: what people earn, spend, borrow and save.",
        "prices, inflation, interest rates, mortgage, rent, bills, taxes, pension, savings, cost of living, wages",
        "Mortgage rates fall as lenders cut prices for homebuyers",
    ],
    "science": [
        "News about scientific discoveries and research about the natural world and space.",
        "scientists, study, research, space, NASA, planet, telescope, physics, biology, climate, species, environment",
        "Scientists discover new species living deep under the ocean",
    ],
    "careers": [
        "News about working life: jobs, hiring and the workplace.",
        "jobs, hiring, layoffs, job cuts, employees, workplace, salary, remote work, recruitment, career, skills",
        "Tech firm cuts hundreds of jobs as it restructures teams",
    ],
    "sports": [
        "News about sport: games, competitions and the athletes who play them.",
        "match, game, team, league, championship, cup, final, coach, player, season, win, score",
        "Team wins championship title after dramatic final game",
    ],
    "entertainment": [
        "News about popular culture: film, TV, music, celebrities and the arts.",
        "film, movie, TV series, actor, singer, album, concert, celebrity, streaming, show, award",
        "Star actor joins cast of hit TV series for new season",
    ],
}
