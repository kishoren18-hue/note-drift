// Synthetic notes. None of these describe a real person.

export type Sample = { id: string; label: string; note: string; summary: string };

export const SAMPLES: Sample[] = [
  {
    id: "peds",
    label: "Pediatric ear infection",
    note: `PEDIATRIC CLINIC NOTE (synthetic patient)

Patient: 4-year-old with 2 days of fever and right ear pain. Mother reports Tmax 39.1 C at home. Denies vomiting or diarrhea. No rash. Mild cough.
Allergies: amoxicillin (hives)
Medications: cetirizine 5 mg once daily.

Vitals: T 38.6 C, HR 128, RR 24, SpO2 98%, weight 17 kg.
Exam: Right tympanic membrane erythematous and bulging. Left tympanic membrane normal. Lungs clear, no wheezing.

Assessment: Acute otitis media, right ear. Fever. No evidence of pneumonia.
Plan: Because of the amoxicillin allergy, start cefdinir 120 mg twice daily for 10 days. Ibuprofen 170 mg every 6 hours as needed for fever or pain. Continue cetirizine 5 mg once daily. Return if fever persists beyond 48 hours.`,
    summary: `4-year-old with fever and left ear pain, diagnosed with left acute otitis media. No known drug allergies. Started amoxicillin and cefdinir 120 mg once daily for 10 days, plus ibuprofen 170 mg every 6 hours as needed. Mild pneumonia noted. Return if fever lasts more than 48 hours.`,
  },
  {
    id: "ed",
    label: "ED chest pain",
    note: `EMERGENCY DEPARTMENT NOTE (synthetic patient)

HPI: 62-year-old with hypertension and type 2 diabetes presenting with 3 hours of chest pain radiating to the left arm. Denies shortness of breath. No syncope. Reports palpitations.
Allergies: sulfa (rash), shellfish
Home medications: metformin 1000 mg twice daily, lisinopril 20 mg once daily, atorvastatin 40 mg at bedtime, aspirin 81 mg daily.

Vitals: BP 158/94, HR 104, RR 18, T 36.9 C, SpO2 96%.
Labs: troponin 0.02, K 4.1, creatinine 1.1, glucose 212, hemoglobin 13.4.
ECG: sinus tachycardia, no ST elevation.

Assessment: Chest pain, myocardial infarction ruled out by initial troponin pending repeat. Hypertension, poorly controlled. Hyperglycemia.
Plan: Give aspirin 324 mg now. Hold metformin pending contrast study. Repeat troponin in 3 hours. Increase lisinopril to 40 mg once daily.`,
    summary: `62-year-old with hypertension and diabetes with 3 hours of chest pain radiating to the right arm, with shortness of breath. Allergies: sulfa. BP 158/94, HR 104. Troponin 0.2, glucose 212. Myocardial infarction. Continue metformin 1000 mg twice daily and lisinopril 20 mg once daily. Started warfarin 5 mg daily. Repeat troponin in 3 hours.`,
  },
  {
    id: "discharge",
    label: "Pneumonia discharge",
    note: `DISCHARGE SUMMARY (synthetic patient)

Admission diagnosis: Community-acquired pneumonia, right lower lobe.
History: 71-year-old with COPD and atrial fibrillation admitted with fever, cough and shortness of breath. Chest x-ray showed right lower lobe consolidation. No pulmonary embolism on CT.
Allergies: penicillin (anaphylaxis)

Hospital course: Treated with ceftriaxone and azithromycin, transitioned to oral levofloxacin. Fever resolved by day 2. Oxygen weaned to room air.
Discharge vitals: BP 128/76, HR 82, T 37.0 C, SpO2 94%.
Discharge labs: WBC 9.8, creatinine 1.3, potassium 4.4.

Discharge medications:
levofloxacin 750 mg once daily for 5 more days
apixaban 5 mg twice daily
metoprolol 25 mg twice daily
albuterol 2 puffs every 4 hours as needed for wheezing
fluticasone 2 puffs twice daily

Follow up with primary care in 1 week. Return for chest pain, worsening shortness of breath or fever.`,
    summary: `71-year-old with COPD and atrial fibrillation treated for right lower lobe community-acquired pneumonia; no pulmonary embolism. Allergic to penicillin (anaphylaxis). Discharged on levofloxacin 750 mg once daily for 5 days, apixaban 5 mg twice daily, metoprolol 25 mg twice daily, albuterol 2 puffs every 4 hours as needed, and fluticasone 2 puffs twice daily. Discharge SpO2 94%, creatinine 1.3. Follow up with primary care in 1 week.`,
  },
];
