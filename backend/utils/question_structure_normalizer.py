def normalize_question_structure(parsed_data):

    if "sections" in parsed_data:
        return parsed_data

    if "questions" not in parsed_data:
        return {"sections": []}

    sections = []

    for q in parsed_data["questions"]:

        section_name = q.get("question_number", "Q")
        per_marks = q.get("per_question_marks", 0)

        sub_questions = []

        for index, sub in enumerate(q.get("sub_questions", [])):

            sub_id = chr(97 + index)  # a,b,c,d

            sub_questions.append({
                "sub_id": sub_id,
                "text": sub.get("text", ""),
                "marks": per_marks
            })

        sections.append({
            "section_name": section_name,
            "questions": [
                {
                    "question_id": section_name,
                    "sub_questions": sub_questions
                }
            ]
        })

    return {"sections": sections}