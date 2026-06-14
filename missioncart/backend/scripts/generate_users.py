"""Generate reproducible simulated MissionCart user profiles."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


random.seed(42)

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BACKEND_DIR / "app" / "data" / "simulated" / "users.json"

CITIES = [
    {"city": "Bangalore", "pincode": "560001", "tier": 1},
    {"city": "Mumbai", "pincode": "400001", "tier": 1},
    {"city": "Delhi", "pincode": "110001", "tier": 1},
    {"city": "Chennai", "pincode": "600001", "tier": 1},
    {"city": "Hyderabad", "pincode": "500001", "tier": 1},
    {"city": "Pune", "pincode": "411001", "tier": 1},
    {"city": "Kolkata", "pincode": "700001", "tier": 1},
    {"city": "Ahmedabad", "pincode": "380001", "tier": 2},
    {"city": "Jaipur", "pincode": "302001", "tier": 2},
    {"city": "Lucknow", "pincode": "226001", "tier": 2},
    {"city": "Kochi", "pincode": "682001", "tier": 2},
    {"city": "Indore", "pincode": "452001", "tier": 2},
]

FIRST_NAMES = [
    "Sneha", "Arjun", "Priya", "Rahul", "Ananya", "Vikram", "Kavya",
    "Rohan", "Meera", "Aditya", "Pooja", "Kiran", "Divya", "Saurabh",
    "Nisha", "Amit", "Shreya", "Varun", "Pallavi", "Nikhil", "Swati",
    "Rohit", "Deepika", "Manish", "Anjali", "Suresh", "Lakshmi", "Ravi",
    "Sunita", "Vijay", "Geeta", "Manoj", "Rekha", "Sunil", "Shweta",
    "Rajesh", "Nandini", "Sanjay", "Usha", "Praveen", "Madhuri", "Harish",
    "Jyoti", "Dinesh", "Sangita", "Rakesh", "Vani", "Ajay", "Saroja",
    "Mohan",
]

LAST_NAMES = [
    "Sharma", "Mehta", "Nair", "Gupta", "Iyer", "Reddy", "Joshi", "Singh",
    "Kumar", "Patel", "Rao", "Verma", "Agarwal", "Malhotra", "Pillai",
    "Menon", "Bhat", "Hegde", "Naik", "Desai", "Kulkarni", "Chavan",
    "More", "Patil", "Shinde", "Tiwari", "Mishra", "Pandey", "Dubey",
    "Srivastava", "Banerjee", "Chatterjee", "Das", "Bose", "Ghosh",
    "Krishnan", "Subramanian", "Murugan", "Rajan", "Venkat", "Choudhary",
    "Shah", "Trivedi", "Parikh", "Bhatt", "Nambiar", "Warrier", "Kurup",
    "Menon", "Namboothiri",
]

IDENTITY_GROUPS_POOL = [
    ["home_chef", "new_parent"],
    ["office_gym_dad", "weekend_trekker"],
    ["jee_student", "college_girl"],
    ["home_chef", "weekend_trekker"],
    ["new_parent", "office_gym_dad"],
    ["college_girl", "home_chef"],
    ["weekend_trekker", "jee_student"],
    ["office_gym_dad", "home_chef"],
    ["new_parent", "home_chef"],
    ["college_girl", "weekend_trekker"],
]

LANGUAGES = ["en", "hi", "en", "en", "hi", "en", "ta", "te", "kn", "ml"]
AGE_BRACKETS = ["18-22", "22-28", "28-35", "35-45", "45-55", "55+"]
AGE_WEIGHTS = [10, 20, 30, 25, 10, 5]
OCCUPATIONS = [
    "Software Engineer", "Teacher", "Doctor", "Business Owner", "Student",
    "Homemaker", "Marketing Manager", "Accountant", "Government Employee",
    "Freelancer",
]

DEMO_USERS = [
    {
        "user_id": "U001",
        "name": "Sneha Sharma",
        "city": "Bangalore",
        "pincode": "560001",
        "identity_groups": ["home_chef", "new_parent"],
        "household_size": 4,
        "amazon_prime": True,
        "preferred_language": "en",
        "monthly_grocery_budget": 8000,
        "created_at": "2024-01-15",
        "demo_user": True,
        "tier": 1,
        "age_bracket": "28-35",
        "occupation": "Software Engineer",
        "occasions_per_year": 6,
    },
    {
        "user_id": "U002",
        "name": "Arjun Mehta",
        "city": "Mumbai",
        "pincode": "400001",
        "identity_groups": ["office_gym_dad", "weekend_trekker"],
        "household_size": 3,
        "amazon_prime": True,
        "preferred_language": "hi",
        "monthly_grocery_budget": 6000,
        "created_at": "2024-03-20",
        "demo_user": False,
        "tier": 1,
        "age_bracket": "32-40",
        "occupation": "Marketing Manager",
        "occasions_per_year": 4,
    },
    {
        "user_id": "U003",
        "name": "Priya Nair",
        "city": "Chennai",
        "pincode": "600001",
        "identity_groups": ["jee_student", "college_girl"],
        "household_size": 1,
        "amazon_prime": False,
        "preferred_language": "en",
        "monthly_grocery_budget": 3000,
        "created_at": "2024-06-01",
        "demo_user": False,
        "tier": 1,
        "age_bracket": "18-22",
        "occupation": "Student",
        "occasions_per_year": 3,
    },
]


def generate_users() -> list[dict]:
    users = list(DEMO_USERS)
    demo_cities = {user["city"] for user in DEMO_USERS}
    uncovered_cities = [
        city_data for city_data in CITIES
        if city_data["city"] not in demo_cities
    ]
    for index in range(3, 50):
        user_id = f"U{index + 1:03d}"
        uncovered_index = index - 3
        city_data = (
            uncovered_cities[uncovered_index]
            if uncovered_index < len(uncovered_cities)
            else random.choice(CITIES)
        )
        created = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 540))
        users.append(
            {
                "user_id": user_id,
                "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "city": city_data["city"],
                "pincode": city_data["pincode"],
                "identity_groups": random.choice(IDENTITY_GROUPS_POOL),
                "household_size": random.choices(
                    [1, 2, 3, 4, 5, 6], weights=[10, 15, 25, 30, 15, 5]
                )[0],
                "amazon_prime": random.random() > 0.35,
                "preferred_language": random.choice(LANGUAGES),
                "monthly_grocery_budget": random.choice(
                    [3000, 4000, 5000, 6000, 7000, 8000, 10000, 12000]
                ),
                "created_at": created.strftime("%Y-%m-%d"),
                "demo_user": False,
                "tier": city_data["tier"],
                "age_bracket": random.choices(
                    AGE_BRACKETS, weights=AGE_WEIGHTS
                )[0],
                "occupation": random.choice(OCCUPATIONS),
                "occasions_per_year": random.choices(
                    [2, 3, 4, 5, 6, 8, 10],
                    weights=[10, 20, 25, 20, 15, 7, 3],
                )[0],
            }
        )
    return users


def main() -> None:
    users = generate_users()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(users, file, indent=2)

    print(f"Generated {len(users)} users")
    print(f"Cities: {len({user['city'] for user in users})} unique")
    print(f"Prime users: {sum(user['amazon_prime'] for user in users)}")
    print(f"Demo users: {sum(user.get('demo_user', False) for user in users)}")


if __name__ == "__main__":
    main()
