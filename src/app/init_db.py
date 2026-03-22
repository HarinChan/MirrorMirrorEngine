
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
from datetime import datetime, timedelta
import bcrypt
import hashlib

CLIENT_HASH_SALT = 'penpals-client-salt'

def client_hash(password: str) -> str:
    data = f"{CLIENT_HASH_SALT}:{password}".encode()
    return hashlib.sha256(data).hexdigest()

def init_db():
    with application.app_context():
        # Re-create tables
        db.drop_all()
        db.create_all()
        print("Database tables re-created successfully!")

        # 1. Create a default account for "Me"
        me_password = bcrypt.hashpw(client_hash("Test1234!").encode(), bcrypt.gensalt(10)).decode()
        me_account = Account(email="me@penpals.com", password_hash=me_password, organization="My School")
        db.session.add(me_account)
        db.session.commit()

        # Create "My" classroom profile
        me_profile = Profile(
            account_id=me_account.id,
            name="PenPals classroom",
            location="London, UK",
            latitude="51.5074",
            longitude="-0.1278",
            class_size=25,
            availability={"Mon": [9, 10, 11], "Wed": [14, 15]},
            interests=["Maths", "Science"]
        )
        db.session.add(me_profile)
        db.session.commit()
        
        # Create Notifications for Me
        n1 = Notification(
            account_id=me_account.id,
            title="New Friend Request",
            message="Philipp's class sent you a friend request.",
            type="info",
            created_at=datetime.utcnow() - timedelta(minutes=30)
        )
        n2 = Notification(
            account_id=me_account.id,
            title="Meeting Reminder",
            message="Your meeting with Harin's class starts in 1 hour.",
            type="warning",
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add_all([n1, n2])
        db.session.commit()

        # 2. Create other classrooms
        classrooms_data = [
                { "name": "Philipp's class", "location": 'Oldenburg, Germany', "lon": 8.2146, "lat": 53.1435, "interests": ['Computer Science'], "availability": { "Mon": [8, 10, 13, 16], "Tue": [9, 11, 14], "Wed": [8, 12, 15], "Thu": [10, 13, 16], "Fri": [8, 9, 14] } },
                { "name": "Parn's class", "location": 'Bangkok, Thailand', "lon": 100.5018, "lat": 13.7563, "interests": [], "availability": { "Mon": [9, 12, 15], "Tue": [8, 11, 13], "Wed": [10, 14, 16], "Thu": [8, 12, 15], "Fri": [9, 11, 14] } },
                { "name": "Ali's class", "location": 'Casablanca, Morocco', "lon": -7.5898, "lat": 33.5731, "interests": ['Physics', 'Debate', 'STEM Projects'], "availability": { "Mon": [8, 11, 14], "Tue": [9, 12, 16], "Wed": [8, 10, 13], "Thu": [11, 14, 15], "Fri": [9, 12, 14] } },
                { "name": "Rhin's class", "location": 'Suwon, South Korea', "lon": 127.0286, "lat": 37.2636, "interests": ['History'], "availability": { "Mon": [14, 16], "Tue": [14, 15], "Wed": [15, 16], "Thu": [14, 16], "Fri": [14, 15] } },
                { "name": "Harin's class", "location": 'Hong Kong', "lon": 114.1694, "lat": 22.3193, "interests": ['Art'], "availability": { "Mon": [8, 10, 13], "Tue": [9, 11, 15], "Wed": [8, 12, 14], "Thu": [10, 13, 16], "Fri": [9, 12, 15] } },
                { "name": 'Rio Harbor Classroom', "location": 'Rio de Janeiro, Brazil', "lon": -43.1729, "lat": -22.9068, "interests": ['Portuguese', 'Geography', 'Environmental Science'], "availability": { "Mon": [8, 11, 16], "Tue": [9, 13, 15], "Wed": [10, 12, 14], "Thu": [8, 11, 15], "Fri": [9, 13, 16] } },
                { "name": 'Pacific Maple Academy', "location": 'Vancouver, Canada', "lon": -123.1207, "lat": 49.2827, "interests": ['Literature', 'Computer Science', 'Film'], "availability": { "Mon": [9, 12, 15], "Tue": [8, 10, 14], "Wed": [9, 11, 16], "Thu": [8, 13, 15], "Fri": [10, 12, 14] } },
                { "name": 'Hudson Learning Studio', "location": 'New York, USA', "lon": -74.0060, "lat": 40.7128, "interests": ['Maths', 'Music', 'Creative Writing'], "availability": { "Mon": [8, 10, 14], "Tue": [9, 12, 15], "Wed": [8, 11, 13], "Thu": [10, 12, 16], "Fri": [9, 14, 15] } },
                { "name": 'Safari Surfers', "location": 'Nairobi, Kenya', "lon": 36.8219, "lat": -1.2921, "interests": ['Biology', 'Civic Studies', 'Poetry'], "availability": { "Mon": [8, 12, 14], "Tue": [9, 11, 15], "Wed": [10, 13, 16], "Thu": [8, 11, 14], "Fri": [9, 12, 15] } },
                { "name": 'Desert Future School', "location": 'Dubai, UAE', "lon": 55.2708, "lat": 25.2048, "interests": ['Engineering', 'Business', 'Robotics'], "availability": { "Mon": [8, 12, 16], "Tue": [9, 11, 14], "Wed": [10, 13, 15], "Thu": [8, 12, 14], "Fri": [9, 11, 16] } },
                { "name": 'Yamuna Scholars Circle', "location": 'New Delhi, India', "lon": 77.2090, "lat": 28.6139, "interests": ['History', 'Hindi', 'Astronomy'], "availability": { "Mon": [8, 10, 15], "Tue": [9, 12, 14], "Wed": [8, 11, 16], "Thu": [10, 13, 15], "Fri": [9, 12, 16] } },
                { "name": 'Marina Innovation Class', "location": 'Singapore', "lon": 103.8198, "lat": 1.3521, "interests": ['Computer Science', 'Maths', 'Robotics'], "availability": { "Mon": [9, 11, 14], "Tue": [8, 10, 15], "Wed": [9, 12, 16], "Thu": [8, 11, 13], "Fri": [10, 12, 15] } },
                { "name": 'Sakura Study Space', "location": 'Tokyo, Japan', "lon": 139.6917, "lat": 35.6895, "interests": ['Japanese', 'Technology', 'History'], "availability": { "Mon": [8, 11, 13], "Tue": [9, 12, 15], "Wed": [10, 14, 16], "Thu": [8, 11, 15], "Fri": [9, 13, 14] } },
                { "name": 'Southern Cross Classroom', "location": 'Sydney, Australia', "lon": 151.2093, "lat": -33.8688, "interests": ['Biology', 'Geography', 'Marine Science'], "availability": { "Mon": [8, 10, 14], "Tue": [9, 12, 16], "Wed": [8, 11, 15], "Thu": [10, 13, 14], "Fri": [9, 12, 15] } },
                { "name": 'Bund Skyline Academy', "location": 'Shanghai, China', "lon": 121.4737, "lat": 31.2304, "interests": ['Mandarin', 'Maths', 'World History'], "availability": { "Mon": [8, 12, 15], "Tue": [9, 11, 14], "Wed": [10, 13, 16], "Thu": [8, 11, 15], "Fri": [9, 12, 14] } },
                { "name": 'Andalusian Bridge Class', "location": 'Seville, Spain', "lon": -5.9845, "lat": 37.3891, "interests": ['Spanish', 'Art', 'History'], "availability": { "Mon": [9, 12, 14], "Tue": [8, 11, 15], "Wed": [10, 13, 16], "Thu": [8, 12, 14], "Fri": [9, 11, 15] } },
            ]

        created_profiles = []
        for c in classrooms_data:
            # Create a dummy account for each classroom
            email = f"{c['name'].replace(' ', '').lower()}@penpals.com"
            pwd = bcrypt.hashpw(client_hash("Test1234!").encode(), bcrypt.gensalt(10)).decode()
            account = Account(email=email, password_hash=pwd, organization="Global School")
            db.session.add(account)
            db.session.commit()
            
            profile = Profile(
                account_id=account.id,
                name=c['name'],
                location=c['location'],
                latitude=str(c['lat']),
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
        philipp = next(p for p in created_profiles if "Philipp" in p.name)
        rhin = next(p for p in created_profiles if "Rhin" in p.name)
        harin = next(p for p in created_profiles if "Harin" in p.name)
        
        # Add Recent Calls for Me
        c1 = RecentCall(
            caller_profile_id=me_profile.id,
            target_classroom_id=str(philipp.id),
            target_classroom_name=philipp.name,
            duration_seconds=300,
            timestamp=datetime.utcnow() - timedelta(days=1),
            call_type="outgoing"
        )
        c2 = RecentCall(
            caller_profile_id=me_profile.id,
            target_classroom_id=str(rhin.id),
            target_classroom_name=rhin.name,
            duration_seconds=1240,
            timestamp=datetime.utcnow() - timedelta(days=2),
            call_type="incoming"
        )
        db.session.add_all([c1, c2])

        posts = []
        
        # Post 1
        p1 = Post(
            profile_id=harin.id,
            content="Hello everyone! We just started our unit on visual storytelling. Would love to connect with another class to share student artwork.",
            likes=12,
            comments_count=2,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add(p1)
        
        # Post 2
        p2 = Post(
            profile_id=philipp.id,
            content="Our students just wrapped up an intro coding challenge and built some fun mini games.",
            likes=45,
            comments_count=5,
            created_at=datetime.utcnow() - timedelta(hours=5)
        )
        db.session.add(p2)
        
        # Post 3 - Quote
        p3 = Post(
            profile_id=rhin.id,
            content="This looks amazing!",
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
        philipp = next(p for p in created_profiles if "Philipp" in p.name)
        rhin = next(p for p in created_profiles if "Rhin" in p.name)
        harin = next(p for p in created_profiles if "Harin" in p.name)

        # Make Harin a friend of Me (Accepted)
        rel1 = Relation(from_profile_id=me_profile.id, to_profile_id=harin.id)
        rel2 = Relation(from_profile_id=harin.id, to_profile_id=me_profile.id)
        db.session.add_all([rel1, rel2])
        
        # Make Philipp send a request to Me (Pending)
        freq1 = FriendRequest(
            sender_profile_id=philipp.id,
            receiver_profile_id=me_profile.id, 
            status='pending'
        )
        db.session.add(freq1)

        # Make Me send a request to Rhin (Pending)
        freq2 = FriendRequest(
            sender_profile_id=me_profile.id,
            receiver_profile_id=rhin.id,
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