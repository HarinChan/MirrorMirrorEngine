
# Load environment variables from .env file before importing main
from dotenv import load_dotenv
load_dotenv()
from .main import application
from .model import db
from .model.account import Account
from .model.profile import Profile
from .model.post import Post
from .model.notification import Notification
from .model.recentcall import RecentCall
from .model.friendrequest import FriendRequest
from .model.relation import Relation

#from models import FriendRequest, Relation
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def init_db():
    with application.app_context():
        # Re-create tables
        db.drop_all()
        db.create_all()
        print("Database tables re-created successfully!")

        # 1. Create a default account for "Me"
        me_password = generate_password_hash("Metest123!")
        me_account = Account(email="me@penpals.com", password_hash=me_password, organization="My School")
        db.session.add(me_account)
        db.session.commit()

        # Create "My" classroom profile
        me_profile = Profile(
            account_id=me_account.id,
            name="My Classroom",
            location="London, UK",
            lattitude="51.5074",
            longitude="-0.1278",
            class_size=25,
            availability={"Mon": [9, 10, 11], "Wed": [14, 15]},
            interests=["Math", "Science"]
        )
        db.session.add(me_profile)
        db.session.commit()
        
        # Create Notifications for Me
        n1 = Notification(
            account_id=me_account.id,
            title="New Friend Request",
            message="Lee's Classroom sent you a friend request.",
            type="info",
            created_at=datetime.utcnow() - timedelta(minutes=30)
        )
        n2 = Notification(
            account_id=me_account.id,
            title="Meeting Reminder",
            message="Your meeting with Sakura Study Space starts in 1 hour.",
            type="warning",
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add_all([n1, n2])
        db.session.commit()

        # 2. Create other Classrooms (from MapView.tsx data)
        classrooms_data = [
          { "name": "Lee's Classroom", "location": 'New York, USA', "lon": -74.0060, "lat": 40.7128, "interests": ['Math', 'Biology', 'Rock Climbing'], "availability": { "Mon": [9, 10, 11, 14, 15], "Tue": [9, 10, 11], "Wed": [14, 15, 16], "Thu": [9, 10, 11], "Fri": [14, 15] } },
          { "name": 'Math Lover House', "location": 'Los Angeles, USA', "lon": -118.2437, "lat": 34.0522, "interests": ['Math', 'Physics', 'Chess'], "availability": { "Mon": [10, 11, 12, 13], "Tue": [10, 11, 12], "Wed": [15, 16, 17], "Thu": [10, 11], "Fri": [14, 15, 16] } },
          { "name": 'The Book Nook', "location": 'Bangkok, Thailand', "lon": 100.518, "lat": 13.7563, "interests": ['English', 'History', 'Creative Writing'], "availability": { "Mon": [9, 10, 11], "Tue": [14, 15, 16], "Wed": [9, 10, 11], "Thu": [14, 15, 16], "Fri": [9, 10] } },
          { "name": "Marie's Language Lab", "location": 'Paris, France', "lon": 2.3522, "lat": 48.8566, "interests": ['French', 'Spanish', 'Mandarin'], "availability": { "Mon": [8, 9, 10], "Tue": [8, 9, 10, 11], "Wed": [14, 15], "Thu": [8, 9, 10], "Fri": [14, 15, 16] } },
          { "name": 'Sakura Study Space', "location": 'Tokyo, Japan', "lon": 139.6917, "lat": 35.6895, "interests": ['Japanese', 'Anime', 'Calligraphy', 'Math'], "availability": { "Mon": [13, 14, 15], "Tue": [13, 14, 15, 16], "Wed": [13, 14], "Thu": [14, 15, 16], "Fri": [13, 14, 15] } },
          { "name": 'Outback Learning Hub', "location": 'Sydney, Australia', "lon": 151.2093, "lat": -33.8688, "interests": ['Biology', 'Geography', 'Surfing'], "availability": { "Mon": [7, 8, 9], "Tue": [7, 8, 9, 10], "Wed": [16, 17, 18], "Thu": [7, 8, 9], "Fri": [16, 17, 18] } },
          { "name": 'TechHub Singapore', "location": 'Singapore', "lon": 103.8198, "lat": 1.3521, "interests": ['Computer Science', 'Robotics', 'Math'], "availability": { "Mon": [10, 11, 12, 13], "Tue": [10, 11, 12], "Wed": [14, 15, 16], "Thu": [10, 11, 12], "Fri": [14, 15] } },
          { "name": "Priya's Practice Room", "location": 'Mumbai, India', "lon": 72.8777, "lat": 19.0760, "interests": ['Hindi', 'Music', 'Dance', 'Math'], "availability": { "Mon": [15, 16, 17], "Tue": [15, 16, 17], "Wed": [9, 10, 11], "Thu": [15, 16, 17], "Fri": [9, 10, 11] } },
          { "name": 'Samba Study Circle', "location": 'São Paulo, Brazil', "lon": -46.6333, "lat": -23.5505, "interests": ['Portuguese', 'Music', 'Dance', 'Biology'], "availability": { "Mon": [11, 12, 13], "Tue": [11, 12, 13, 14], "Wed": [16, 17, 18], "Thu": [11, 12, 13], "Fri": [16, 17] } },
          { "name": 'Alpine Academic Circle', "location": 'Gstaad, Switzerland', "lon": 46.4722, "lat": 7.2869, "interests": ['German', 'Chemistry', 'Physics', 'Hiking'], "availability": { "Mon": [8, 9, 10, 11], "Tue": [14, 15, 16], "Wed": [8, 9, 10], "Thu": [14, 15, 16], "Fri": [8, 9, 10] } },
          { "name": 'The Knit & Wit', "location": 'Stockholm, Sweden', "lon": 18.0686, "lat": 59.3293, "interests": ['Knitting', 'Crafts', 'Design', 'Swedish'], "availability": { "Mon": [13, 14, 15], "Tue": [9, 10, 11], "Wed": [13, 14, 15], "Thu": [9, 10, 11], "Fri": [13, 14, 15] } },
          { "name": 'Seoul Study Station', "location": 'Seoul, South Korea', "lon": 126.9780, "lat": 37.5665, "interests": ['Korean', 'K-Pop', 'Art', 'Math'], "availability": { "Mon": [16, 17, 18], "Tue": [10, 11, 12], "Wed": [16, 17, 18], "Thu": [10, 11, 12], "Fri": [16, 17] } },
        ]

        created_profiles = []
        for c in classrooms_data:
            # Create a dummy account for each classroom
            email = f"{c['name'].replace(' ', '').lower()}@penpals.com"
            pwd = generate_password_hash("Test1234!")
            account = Account(email=email, password_hash=pwd, organization="Global School")
            db.session.add(account)
            db.session.commit()
            
            profile = Profile(
                account_id=account.id,
                name=c['name'],
                location=c['location'],
                lattitude=str(c['lat']),
                longitude=str(c['lon']),
                class_size=20,
                availability=c['availability'],
                interests=c['interests']
            )
            db.session.add(profile)
            created_profiles.append(profile)
        
        db.session.commit()
        print(f"Created {len(created_profiles)} classrooms")

        # 3. Create Posts and Calls
        
        # Get reference to some profiles
        marie = next(p for p in created_profiles if "Marie" in p.name)
        lee = next(p for p in created_profiles if "Lee" in p.name)
        sakura = next(p for p in created_profiles if "Sakura" in p.name)
        
        # Add Recent Calls for Me
        c1 = RecentCall(
            caller_profile_id=me_profile.id,
            target_classroom_id=str(lee.id),
            target_classroom_name=lee.name,
            duration_seconds=300,
            timestamp=datetime.utcnow() - timedelta(days=1),
            call_type="outgoing"
        )
        c2 = RecentCall(
            caller_profile_id=me_profile.id,
            target_classroom_id=str(sakura.id),
            target_classroom_name=sakura.name,
            duration_seconds=1240,
            timestamp=datetime.utcnow() - timedelta(days=2),
            call_type="incoming"
        )
        db.session.add_all([c1, c2])

        posts = []
        
        # Post 1
        p1 = Post(
            profile_id=marie.id,
            content="Hello everyone! We just started our unit on French Impressionism. Would love to connect with an art class to share our student's work! 🎨🇫🇷",
            likes=12,
            comments_count=2,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add(p1)
        
        # Post 2 - Image
        p2 = Post(
            profile_id=lee.id,
            content="Our science fair projects are finally done! The students worked so hard on their volcanoes. 🌋",
            image_url="https://images.unsplash.com/photo-1596495578065-6e0763fa1178?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80",
            likes=45,
            comments_count=5,
            created_at=datetime.utcnow() - timedelta(hours=5)
        )
        db.session.add(p2)
        
        # Post 3 - Quote
        p3 = Post(
            profile_id=sakura.id,
            content="This looks amazing! We would love to do a video call to see them in action. Our students are learning about geology right now.",
            quoted_post=p2,
            likes=8,
            comments_count=1,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(p3)
        
        db.session.commit()
        print("Created synthetic posts and calls")

        # 4. Create Friendships and Requests
        
        # Get reference to some profiles
        marie = next(p for p in created_profiles if "Marie" in p.name)
        lee = next(p for p in created_profiles if "Lee" in p.name)
        sakura = next(p for p in created_profiles if "Sakura" in p.name)

        # Make Marie a friend of Me (Accepted)
        rel1 = Relation(from_profile_id=me_profile.id, to_profile_id=marie.id)
        rel2 = Relation(from_profile_id=marie.id, to_profile_id=me_profile.id)
        db.session.add_all([rel1, rel2])
        
        # Make Lee send a request to Me (Pending)
        freq1 = FriendRequest(
            sender_profile_id=lee.id,
            receiver_profile_id=me_profile.id, 
            status='pending'
        )
        db.session.add(freq1)

        # Make Me send a request to Sakura (Pending)
        freq2 = FriendRequest(
            sender_profile_id=me_profile.id,
            receiver_profile_id=sakura.id,
            status='pending'
        )
        db.session.add(freq2)

        # # 5. Create Meetings
        # from models import Meeting
        
        # meeting1 = Meeting(
        #     title="Cultural Exchange: UK & Japan",
        #     start_time=datetime.utcnow() + timedelta(days=1, hours=2),
        #     end_time=datetime.utcnow() + timedelta(days=1, hours=3),
        #     creator_id=me_profile.id,
        #     web_link="https://meet.google.com/abc-defg-hij" # Mock link
        # )
        # meeting1.participants.append(sakura)
        # db.session.add(meeting1)
        
        db.session.commit()
        print("Created synthetic friends and meetings")

if __name__ == '__main__':
    init_db()