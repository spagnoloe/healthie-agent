"""Patient lookup tool.

Dummy implementation for now. Will be backed by Healthie (or another EHR)
in a future PR. The flow layer calls this function without knowing
which backend fulfills the request.
"""


async def find_patient(name: str, date_of_birth: str) -> dict | None:
    """Look up a patient by name and date of birth.

    Args:
        name: The patient's full name.
        date_of_birth: The patient's date of birth (YYYY-MM-DD).

    Returns:
        dict with patient_id, name, date_of_birth if found, or None.
    """
    # TODO: Implement patient search functionality using Playwright
    # 1. Ensure you're logged in by calling login_to_healthie()
    # 2. Enter the patient's name and date of birth into the search field
    # 3. Submit the search
    # 4. Parse the results and return patient information
    # 5. Handle cases where the patient is not found
    return {"patient_id": "dummy-123", "name": name, "date_of_birth": date_of_birth}
