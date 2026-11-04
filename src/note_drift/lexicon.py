"""Small built-in vocabularies. Extend them, or pass your own to `extract`.

These are intentionally modest; the extractor also catches any unknown drug
written as "<word> <number> <unit>". For production use, swap in RxNorm and
SNOMED/ICD vocabularies.
"""

MEDICATIONS = {
    "acetaminophen", "albuterol", "allopurinol", "alprazolam", "amiodarone", "amlodipine",
    "amoxicillin", "amoxicillin-clavulanate", "apixaban", "aspirin", "atenolol", "atorvastatin",
    "azithromycin", "budesonide", "bupropion", "carvedilol", "cefdinir", "ceftriaxone", "cephalexin",
    "cetirizine", "ciprofloxacin", "citalopram", "clonazepam", "clopidogrel", "cyclobenzaprine",
    "dexamethasone", "diazepam", "digoxin", "diltiazem", "diphenhydramine", "doxycycline",
    "duloxetine", "enoxaparin", "escitalopram", "famotidine", "fentanyl", "fluoxetine",
    "fluticasone", "furosemide", "gabapentin", "glipizide", "heparin", "hydralazine",
    "hydrochlorothiazide", "hydrocodone", "hydroxyzine", "ibuprofen", "insulin", "ipratropium",
    "ketorolac", "lamotrigine", "levetiracetam", "levofloxacin", "levothyroxine", "lisinopril",
    "loratadine", "lorazepam", "losartan", "meloxicam", "metformin", "methylphenidate",
    "methylprednisolone", "metoprolol", "metronidazole", "montelukast", "morphine", "naloxone",
    "naproxen", "nitrofurantoin", "nitroglycerin", "omeprazole", "ondansetron", "oxycodone",
    "pantoprazole", "penicillin", "potassium chloride", "pravastatin", "prednisolone", "prednisone",
    "propranolol", "quetiapine", "rivaroxaban", "rosuvastatin", "sertraline", "simvastatin",
    "spironolactone", "sulfamethoxazole-trimethoprim", "tamsulosin", "tramadol", "trazodone",
    "valacyclovir", "vancomycin", "warfarin", "zolpidem",
}

# common allergens beyond drugs
ALLERGENS = {
    "peanuts", "peanut", "tree nuts", "shellfish", "eggs", "egg", "milk", "latex", "sulfa",
    "iodine", "contrast", "bee stings", "codeine", "nsaids", "soy", "wheat", "penicillins",
}

CONDITIONS = {
    "asthma", "pneumonia", "otitis media", "bronchiolitis", "fever", "cough", "wheezing",
    "chest pain", "shortness of breath", "dyspnea", "hypertension", "diabetes", "type 2 diabetes",
    "type 1 diabetes", "hyperlipidemia", "atrial fibrillation", "heart failure", "copd", "stroke",
    "myocardial infarction", "pulmonary embolism", "deep vein thrombosis", "dvt", "sepsis",
    "urinary tract infection", "uti", "cellulitis", "appendicitis", "migraine", "headache",
    "seizure", "syncope", "nausea", "vomiting", "diarrhea", "abdominal pain", "rash", "anemia",
    "chronic kidney disease", "ckd", "hypothyroidism", "depression", "anxiety", "adhd",
    "obesity", "dehydration", "fracture", "concussion", "loss of consciousness", "edema",
    "palpitations", "dizziness", "sore throat", "strep pharyngitis", "eczema", "croup",
}

LAB_NAMES = {
    "wbc": "wbc", "white blood cell count": "wbc", "hgb": "hemoglobin", "hemoglobin": "hemoglobin",
    "hct": "hematocrit", "platelets": "platelets", "plt": "platelets", "sodium": "sodium",
    "na": "sodium", "potassium": "potassium", "k": "potassium", "creatinine": "creatinine",
    "cr": "creatinine", "bun": "bun", "glucose": "glucose", "a1c": "a1c", "hba1c": "a1c",
    "troponin": "troponin", "inr": "inr", "lactate": "lactate", "crp": "crp", "tsh": "tsh",
}

BODY_PARTS = {
    "arm", "leg", "knee", "ankle", "wrist", "hip", "shoulder", "elbow", "foot", "hand", "ear",
    "eye", "lung", "kidney", "breast", "lower extremity", "upper extremity", "flank", "lower lobe",
    "upper lobe", "tympanic membrane",
}

FREQUENCIES = {
    # normalized form: patterns
    "once daily": [r"once (?:a )?daily", r"daily", r"q\.?d\.?", r"every day", r"once a day", r"qam", r"qpm"],
    "twice daily": [r"twice (?:a )?daily", r"b\.?i\.?d\.?", r"twice a day", r"every 12 hours", r"q12h"],
    "three times daily": [r"three times (?:a )?daily", r"t\.?i\.?d\.?", r"three times a day", r"every 8 hours", r"q8h"],
    "four times daily": [r"four times (?:a )?daily", r"q\.?i\.?d\.?", r"four times a day", r"every 6 hours", r"q6h"],
    "every 4 hours": [r"every 4 hours", r"q4h"],
    "at bedtime": [r"at bedtime", r"nightly", r"q\.?h\.?s\.?"],
    "weekly": [r"weekly", r"once a week"],
    "as needed": [r"as needed", r"p\.?r\.?n\.?"],
}

NEGATION_CUES = [
    "no", "denies", "denied", "negative for", "without", "not", "ruled out", "rules out",
    "free of", "absence of", "no evidence of", "no signs of", "resolved",
]
