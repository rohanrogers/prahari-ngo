"""
Gemini system prompts for the Coordinator Agent.
Exact prompts from BLUEPRINT.md Section 8.
"""

COORDINATOR_SYSTEM_PROMPT = """You are the COORDINATOR agent of PRAHARI-NGO.

A potential crisis has been detected. Your job is to match volunteers from the 
Volunteer Graph to the crisis requirements, rank them by fit, and generate 
ready-to-send outreach messages in their native languages.

YOU HAVE TWO MODES:
1. PRE_STAGED (threat detected, not yet confirmed): Match top 15 candidates, 
   draft messages, but do NOT mark as active. This is proactive preparation.
2. ACTIVE (crisis confirmed): Finalize top 10-20 matches, generate outreach, 
   mark plan as active.

MATCHING PHILOSOPHY:
- Proximity matters most for physical response (rescue, first aid).
- Language matters for coordination and victim communication.
- Skill overlap matters, but overqualified volunteers should be ranked high too.
- Availability within the escalation window is non-negotiable.
- Diversity of skills in the matched set > redundancy.

OUTREACH PHILOSOPHY:
- Write in the volunteer's PRIMARY language, not default English.
- Be specific about need, location, time, role.
- Include a clear yes/no response mechanism.
- Tone: urgent but respectful. NGO volunteers are not employees.

WORKFLOW:
1. Use search_volunteers_semantic for each required skill group
2. Union results, then filter_by_geography with appropriate radius
3. filter_by_availability for the escalation window
4. filter_by_language for regional language coverage
5. rank_volunteers with full crisis context
6. For top 15: generate_outreach_message in their primary language
7. save_response_plan with full reasoning

Always explain your reasoning in the final save_response_plan call."""


OUTREACH_TEMPLATE_ML = """🚨 *{crisis_type} അടിയന്തര സഹായം — {location}*

{volunteer_name}, നമസ്കാരം.

{location_detail} ൽ {crisis_detail}. 
നിങ്ങളുടെ {skill_mention} കഴിവ് ഈ സമയത്ത് അത്യന്ത ആവശ്യമാണ്.

📍 *സ്ഥലം:* {location}
⏰ *സമയം:* ഇപ്പോൾ — {time_window}
🎯 *ആവശ്യം:* {role}

സഹായിക്കാൻ തയ്യാറാണെങ്കിൽ *ஆம்* എന്ന് മറുപടി നൽകുക.
ലഭ്യമല്ലെങ്കിൽ *�ല्ल* എന്ന് മറുപടി നൽകുക.

— Prahari NGO Coordination System"""


OUTREACH_TEMPLATE_HI = """🚨 *{crisis_type} आपातकालीन सहायता — {location}*

{volunteer_name} जी, नमस्ते.

{location_detail} में {crisis_detail}.
आपकी {skill_mention} विशेषज्ञता इस समय बहुत आवश्यक है.

📍 *स्थान:* {location}
⏰ *समय:* अभी — {time_window}
🎯 *भूमिका:* {role}

अगर आप सहायता कर सकते हैं तो *हाँ* उत्तर दें.
अगर उपलब्ध नहीं हैं तो *नहीं* उत्तर दें.

— Prahari NGO Coordination System"""


OUTREACH_TEMPLATE_EN = """🚨 *{crisis_type} Emergency Support — {location}*

Dear {volunteer_name},

A {crisis_detail} has been reported in {location_detail}.
Your {skill_mention} skills are urgently needed.

📍 *Location:* {location}
⏰ *Window:* Now — {time_window}
🎯 *Role:* {role}

Reply *YES* if you can help.
Reply *NO* if unavailable.

— Prahari NGO Coordination System"""


OUTREACH_TEMPLATE_TA = """🚨 *{crisis_type} அவசர உதவி — {location}*

{volunteer_name}, வணக்கம்.

{location_detail} இல் {crisis_detail}.
உங்கள் {skill_mention} திறமை இப்போது மிகவும் தேவை.

📍 *இடம்:* {location}
⏰ *நேரம்:* இப்போது — {time_window}
🎯 *பணி:* {role}

உதவ முடியுமா என்றால் *ஆம்* என பதிலளிக்கவும்.
வாய்ப்பில்லை என்றால் *இல்லை* என பதிலளிக்கவும்.

— Prahari NGO Coordination System"""


OUTREACH_TEMPLATES = {
    "ml": OUTREACH_TEMPLATE_ML,
    "hi": OUTREACH_TEMPLATE_HI,
    "en": OUTREACH_TEMPLATE_EN,
    "ta": OUTREACH_TEMPLATE_TA,
}
