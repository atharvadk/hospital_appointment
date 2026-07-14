import json
import logging
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Google Generative AI (Gemini)
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    HAS_GEMINI = True
else:
    logger.warning(
        "No GEMINI_API_KEY or GOOGLE_API_KEY found. LLM operations will use rule-based fallback defaults."
    )
    HAS_GEMINI = False


def generate_pre_visit_summary(symptoms: str) -> dict:
    """
    Analyse these symptoms and return: urgency level (Low / Medium / High), chief complaint, and three suggested questions for the doctor.
    """
    default_summary = {
        "urgency": "Medium",
        "chief_complaint": symptoms[:100] + "..." if len(symptoms) > 100 else symptoms,
        "questions": [
            "How long have you been experiencing these symptoms?",
            "Have you noticed any triggers that make it worse or better?",
            "Are you currently taking any medications for this?",
        ],
    }

    if not HAS_GEMINI or not symptoms:
        return default_summary

    prompt = (
        "Analyse these symptoms and return: urgency level (Low / Medium / High), chief complaint, "
        "and three suggested questions for the doctor. Symptoms: <symptoms>\n"
        f"Symptoms: {symptoms}\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "{\n"
        '  "urgency": "Low" or "Medium" or "High",\n'
        '  "chief_complaint": "string describing the chief complaint",\n'
        '  "questions": ["question 1", "question 2", "question 3"]\n'
        "}"
    )

    try:
        # Using the standard gemini-1.5-flash model
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown codeblocks if LLM returned them
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        # Validate keys
        if "urgency" in data and "chief_complaint" in data and "questions" in data:
            # Normalize urgency
            urg = data["urgency"].strip().capitalize()
            if urg not in ["Low", "Medium", "High"]:
                urg = "Medium"
            data["urgency"] = urg
            # Ensure questions has 3 items
            if not isinstance(data["questions"], list) or len(data["questions"]) == 0:
                data["questions"] = default_summary["questions"]
            return data
    except Exception as e:
        logger.error(f"Error generating pre-visit summary from Gemini: {e}")
        # Fallback to smart local keywords
        symptoms_lower = symptoms.lower()
        urgency = "Medium"
        if any(
            w in symptoms_lower
            for w in [
                "chest pain",
                "breathing",
                "severe",
                "bleeding",
                "unconscious",
                "stroke",
            ]
        ):
            urgency = "High"
        elif any(w in symptoms_lower for w in ["mild", "itch", "scratch", "sneeze"]):
            urgency = "Low"

        default_summary["urgency"] = urgency
        return default_summary

    return default_summary


def generate_post_visit_summary(clinical_notes: str) -> str:
    """
    Convert these clinical notes into a patient-friendly summary with medication schedule and follow-up steps: <notes>
    """
    default_summary = (
        f"Patient-friendly Summary:\n"
        f"Based on the notes provided, please follow these steps:\n"
        f"- Clinical Notes: {clinical_notes}\n"
        f"- Please rest, stay hydrated, and follow your doctor's prescriptions."
    )

    if not HAS_GEMINI or not clinical_notes:
        return default_summary

    prompt = (
        "Convert these clinical notes into a patient-friendly summary with medication schedule and follow-up steps. "
        f"Notes: {clinical_notes}\n\n"
        "Format the output as a clear, compassionate, and readable message for the patient."
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating post-visit summary from Gemini: {e}")
        return default_summary


def parse_prescription_for_reminders(prescription: str) -> list[dict]:
    """
    Parses a prescription text and extracts structured medication reminders.
    Returns: list of dicts with keys: medication_name, dosage, frequency_hours.
    """
    default_reminders = []
    lines = [line.strip() for line in prescription.split("\n") if line.strip()]
    for line in lines:
        freq = 12
        line_lower = line.lower()
        if (
            "8 hours" in line_lower
            or "8 hrs" in line_lower
            or "3 times" in line_lower
            or "3x" in line_lower
        ):
            freq = 8
        elif (
            "6 hours" in line_lower
            or "6 hrs" in line_lower
            or "4 times" in line_lower
            or "4x" in line_lower
        ):
            freq = 6
        elif (
            "24 hours" in line_lower
            or "once a day" in line_lower
            or "1x" in line_lower
            or "daily" in line_lower
        ):
            freq = 24
        elif (
            "12 hours" in line_lower
            or "12 hrs" in line_lower
            or "twice" in line_lower
            or "2x" in line_lower
        ):
            freq = 12

        parts = line.split("-")
        name = parts[0].strip()
        dosage = parts[1].strip() if len(parts) > 1 else "As directed"
        default_reminders.append(
            {"medication_name": name, "dosage": dosage, "frequency_hours": freq}
        )

    if not HAS_GEMINI or not prescription:
        return default_reminders

    prompt = (
        "Analyze this prescription and extract structured medication reminders.\n"
        f"Prescription:\n{prescription}\n\n"
        "Return ONLY a JSON array of objects, where each object has exactly these keys:\n"
        "[\n"
        "  {\n"
        '    "medication_name": "Name of medication",\n'
        '    "dosage": "dosage instructions (e.g. 1 tablet, 5ml)",\n'
        '    "frequency_hours": integer number representing how often in hours to take it (e.g. 8 for three times a day, 12 for twice a day, 24 for daily)\n'
        "  }\n"
        "]\n"
        "Do not include any markdown syntax, explanation, or code blocks in the output. Return raw JSON only."
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        if isinstance(data, list):
            validated_reminders = []
            for item in data:
                if (
                    "medication_name" in item
                    and "dosage" in item
                    and "frequency_hours" in item
                ):
                    try:
                        item["frequency_hours"] = int(item["frequency_hours"])
                    except ValueError:
                        item["frequency_hours"] = 12
                    validated_reminders.append(item)
            if validated_reminders:
                return validated_reminders
    except Exception as e:
        logger.error(f"Error parsing prescription with Gemini: {e}")

    return default_reminders
