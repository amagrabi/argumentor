
import sys
import os

# Add project root and src to python path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

import unittest.mock
mock_creds = unittest.mock.MagicMock()
unittest.mock.patch('google.oauth2.service_account.Credentials.from_service_account_file', return_value=mock_creds).start()
unittest.mock.patch('google.oauth2.service_account.Credentials.from_service_account_info', return_value=mock_creds).start()

from app import create_app
from models import Answer, db

app = create_app()

with app.app_context():
    answers = Answer.query.order_by(Answer.created_at.desc()).limit(10).all()
    
    if not answers:
        print("No answers found in the database.")
    else:
        print(f"Showing the latest {len(answers)} answers:\n")
        for i, answer in enumerate(answers, 1):
            print(f"--- Answer {i} ---")
            print(f"ID: {answer.id}")
            print(f"User UUID: {answer.user_uuid}")
            print(f"Created At: {answer.created_at}")
            print(f"Question: {answer.question_text}")
            print(f"Claim: {answer.claim}")
            print(f"Argument: {answer.argument}")
            print(f"Counterargument: {answer.counterargument}")
            print(f"Scores: {answer.evaluation_scores}")
            print(f"Feedback: {answer.evaluation_feedback}")
            if answer.challenge_response:
                print(f"Challenge: {answer.challenge}")
                print(f"Challenge Response: {answer.challenge_response}")
                print(f"Challenge Scores: {answer.challenge_evaluation_scores}")
            print("\n")
