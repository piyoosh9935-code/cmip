"""Cohort-specific clinical reference data used to generate realistic-looking (but
entirely synthetic) claims, conditions, medications, and notes. Codes are real ICD-10/
CPT/NDC-style identifiers used for plausibility; nothing here is patient data."""

COHORTS = {
    "diabetes": {
        "conditions": [
            ("E11.9", "Type 2 diabetes mellitus without complications"),
            ("E11.22", "Type 2 diabetes mellitus with diabetic chronic kidney disease"),
            ("E11.40", "Type 2 diabetes mellitus with diabetic neuropathy, unspecified"),
            ("E11.65", "Type 2 diabetes mellitus with hyperglycemia"),
        ],
        "procedures": [
            ("83036", "Hemoglobin A1c test"),
            ("82947", "Glucose, blood quantitative"),
            ("99214", "Office visit, established patient, moderate complexity"),
            ("92014", "Ophthalmological exam, diabetic retinopathy screening"),
        ],
        "medications": [
            "Metformin 1000mg", "Glipizide 5mg", "Insulin glargine (Lantus) 20 units",
            "Empagliflozin 10mg", "Semaglutide 0.5mg injection",
        ],
        "note_templates": [
            "Patient with {years} year history of type 2 diabetes, HbA1c {a1c}%, "
            "reports {adherence} adherence to {med}. {complication}",
            "Diabetes follow-up: fasting glucose {glucose} mg/dL, weight {trend}. "
            "Continuing {med}, will recheck A1c in 3 months.",
            "Diabetic retinopathy screening {result}. Patient counseled on glycemic "
            "control and foot care given {complication_lower}",
        ],
        "vocab": {
            "years": ["2", "5", "8", "12"],
            "a1c": ["6.8", "7.2", "7.9", "8.4", "9.1"],
            "adherence": ["good", "moderate", "poor"],
            "med": ["metformin", "glipizide", "insulin glargine", "empagliflozin"],
            "complication": [
                "No evidence of neuropathy at this time.",
                "Early signs of peripheral neuropathy noted in the feet.",
                "Reports occasional blurred vision, referred to ophthalmology.",
                "Mild proteinuria on recent labs, monitoring renal function.",
            ],
            "glucose": ["118", "142", "165", "190", "210"],
            "trend": ["stable", "down 4 lbs since last visit", "up 6 lbs since last visit"],
            "result": ["negative for retinopathy", "showed mild non-proliferative changes"],
        },
    },
    "hypertension": {
        "conditions": [
            ("I10", "Essential (primary) hypertension"),
            ("I11.9", "Hypertensive heart disease without heart failure"),
            ("I12.9", "Hypertensive chronic kidney disease with stage 1-4 CKD"),
        ],
        "procedures": [
            ("99213", "Office visit, established patient, low complexity"),
            ("93000", "Electrocardiogram, routine"),
            ("80061", "Lipid panel"),
        ],
        "medications": [
            "Lisinopril 20mg", "Amlodipine 5mg", "Hydrochlorothiazide 25mg",
            "Losartan 50mg", "Metoprolol succinate 50mg",
        ],
        "note_templates": [
            "Blood pressure {bp} mmHg today, {trend} from last visit. Currently on "
            "{med}, tolerating well with {side_effect}",
            "Hypertension follow-up. Home readings averaging {bp}. Discussed sodium "
            "reduction and adherence to {med}.",
            "Patient reports {side_effect_report} on {med}. Will consider dose "
            "adjustment if blood pressure remains {trend_desc} at next visit.",
        ],
        "vocab": {
            "bp": ["128/82", "138/88", "145/92", "152/96", "162/100"],
            "trend": ["improved", "unchanged", "worsened"],
            "med": ["lisinopril", "amlodipine", "hydrochlorothiazide", "losartan"],
            "side_effect": ["no reported side effects", "mild ankle swelling", "occasional dizziness"],
            "side_effect_report": ["no side effects", "mild dry cough", "lightheadedness on standing"],
            "trend_desc": ["elevated", "borderline", "well controlled"],
        },
    },
    "chf": {
        "conditions": [
            ("I50.22", "Chronic systolic (congestive) heart failure"),
            ("I50.32", "Chronic diastolic (congestive) heart failure"),
            ("I50.9", "Heart failure, unspecified"),
        ],
        "procedures": [
            ("93306", "Echocardiogram, complete"),
            ("99215", "Office visit, established patient, high complexity"),
            ("94760", "Pulse oximetry"),
        ],
        "medications": [
            "Furosemide 40mg", "Carvedilol 12.5mg", "Sacubitril-valsartan (Entresto) 49-51mg",
            "Spironolactone 25mg",
        ],
        "note_templates": [
            "CHF follow-up: ejection fraction {ef}%, {symptom}. Weight {weight_trend}, "
            "continuing {med} and daily weights at home.",
            "Patient with NYHA class {nyha} heart failure reports {symptom_report}. "
            "No recent hospitalizations. Diuretic dose {diuretic_change}.",
        ],
        "vocab": {
            "ef": ["30", "35", "40", "45"],
            "symptom": ["no acute exacerbation", "mild bilateral lower extremity edema", "increased dyspnea on exertion"],
            "weight_trend": ["stable", "up 3 lbs over past week", "down after diuretic adjustment"],
            "med": ["furosemide", "carvedilol", "sacubitril-valsartan"],
            "nyha": ["I", "II", "III"],
            "symptom_report": ["good exercise tolerance", "shortness of breath climbing stairs", "orthopnea, sleeping on 2 pillows"],
            "diuretic_change": ["unchanged", "increased", "decreased"],
        },
    },
    "copd": {
        "conditions": [
            ("J44.1", "Chronic obstructive pulmonary disease with acute exacerbation"),
            ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
        ],
        "procedures": [
            ("94010", "Spirometry"),
            ("94640", "Nebulizer treatment"),
            ("71046", "Chest X-ray, 2 views"),
        ],
        "medications": [
            "Albuterol inhaler", "Tiotropium (Spiriva) inhaler", "Fluticasone-salmeterol (Advair)",
            "Prednisone 20mg taper",
        ],
        "note_templates": [
            "COPD {status}: FEV1 {fev1}% predicted, {symptom}. On {med}, "
            "{smoking_status}.",
            "Patient presents with {symptom_report}, consistent with COPD "
            "{status_lower}. Started {med}, follow-up in {followup} weeks.",
        ],
        "vocab": {
            "status": ["stable", "mild exacerbation", "acute exacerbation"],
            "fev1": ["42", "55", "61", "70"],
            "symptom": ["baseline dyspnea on exertion", "increased sputum production", "wheezing on exam"],
            "med": ["albuterol inhaler", "tiotropium", "fluticasone-salmeterol"],
            "smoking_status": ["former smoker, quit 5 years ago", "current smoker, counseled on cessation", "never smoker"],
            "symptom_report": ["worsening shortness of breath", "productive cough for 3 days", "chest tightness"],
            "followup": ["2", "4", "6"],
        },
    },
    "depression": {
        "conditions": [
            ("F32.1", "Major depressive disorder, single episode, moderate"),
            ("F33.1", "Major depressive disorder, recurrent, moderate"),
            ("F41.1", "Generalized anxiety disorder"),
        ],
        "procedures": [
            ("90834", "Psychotherapy, 45 minutes"),
            ("99214", "Office visit, established patient, moderate complexity"),
            ("96127", "Brief emotional/behavioral assessment (PHQ-9)"),
        ],
        "medications": [
            "Sertraline 100mg", "Escitalopram 10mg", "Bupropion XL 150mg", "Venlafaxine XR 75mg",
        ],
        "note_templates": [
            "PHQ-9 score {phq9}, {trend} since last visit. Patient reports {symptom} "
            "while taking {med}.",
            "Follow-up for depression/anxiety: {symptom_report}. Continuing {med} "
            "and biweekly therapy sessions.",
        ],
        "vocab": {
            "phq9": ["6", "10", "14", "18"],
            "trend": ["improved", "unchanged", "worsened"],
            "symptom": ["improved sleep and mood", "persistent low energy", "reduced appetite"],
            "med": ["sertraline", "escitalopram", "bupropion", "venlafaxine"],
            "symptom_report": ["engaging well in therapy", "increased anxiety around work stress", "reports better coping strategies"],
        },
    },
}

SDOH_HOUSING = ["stable housing", "at risk of eviction", "temporary/unstable housing", "homeless in past 12 months"]
SDOH_FOOD = ["food secure", "mild food insecurity", "moderate food insecurity", "severe food insecurity"]
SDOH_TRANSPORT = ["reliable transportation", "occasional transportation barriers", "frequent missed appointments due to transportation"]
SDOH_INCOME = ["<100% FPL", "100-200% FPL", "200-400% FPL", ">400% FPL"]

PROVIDER_SPECIALTIES = [
    "Internal Medicine", "Endocrinology", "Cardiology", "Pulmonology",
    "Psychiatry", "Family Medicine", "Nephrology",
]
