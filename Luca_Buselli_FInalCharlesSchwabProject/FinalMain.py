import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
import praw
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func
from prawcore.exceptions import TooManyRequests, NotFound, Forbidden, Redirect
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import openai

# Load environment variables for Reddit and OpenAI API credentials
load_dotenv('.env')
# Set up OpenAI API credentials
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define your MSSQL database connection string
DBServerName = "LUCA"
DBName = "FinalRedditDataDB"

connection_string = f"mssql+pyodbc://@{DBServerName}/{DBName}?driver=ODBC%20Driver%2017%20for%20SQL%20Server&trusted_connection=yes"
engine = create_engine(connection_string)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Initialize VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Define your database models
class User(Base):
    __tablename__ = 'tblUser'
    tblUser_UserID = Column(String(50), primary_key=True)
    tblUser_Username = Column(String(50), nullable=False)
    tblUser_CreatedUTC = Column(DateTime)
    tblUser_CommentKarma = Column(Integer)
    tblUser_LinkKarma = Column(Integer)
    tblUser_IsGold = Column(Boolean)
    tblUser_IsMod = Column(Boolean)
    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")

class Subreddit(Base):
    __tablename__ = 'tblSubreddit'
    tblSubreddit_SubredditID = Column(String(50), primary_key=True)
    tblSubreddit_Name = Column(String(100), nullable=False)
    tblSubreddit_Title = Column(String(255))
    tblSubreddit_Description = Column(Text)
    tblSubreddit_Subscribers = Column(Integer)
    tblSubreddit_ActiveUsers = Column(Integer)
    tblSubreddit_CreatedUTC = Column(DateTime)
    tblSubreddit_Over18 = Column(Boolean)
    tblSubreddit_PublicDescription = Column(Text)
    tblSubreddit_Lang = Column(String(10))
    tblSubreddit_IconImg = Column(Text)
    tblSubreddit_BannerImg = Column(Text)
    tblSubreddit_UserIsSubscriber = Column(Boolean)
    posts = relationship("Post", back_populates="subreddit")

class Post(Base):
    __tablename__ = 'tblPost'
    tblPost_PostID = Column(String(50), primary_key=True)
    tblPost_Title = Column(String(300), nullable=False)
    tblPost_TitleSentiment = Column(Float)  # VADER sentiment score for the title
    tblPost_AuthorID = Column(String(50), ForeignKey('tblUser.tblUser_UserID'), nullable=True)
    tblPost_SubredditID = Column(String(50), ForeignKey('tblSubreddit.tblSubreddit_SubredditID'))
    tblPost_Content = Column(Text)
    tblPost_ContentSentiment = Column(Float)  # VADER sentiment score for the content
    tblPost_URL = Column(Text)
    tblPost_ImageURL = Column(Text)  # Add this line
    tblPost_Score = Column(Integer)
    tblPost_UpvoteRatio = Column(Float)
    tblPost_NumComments = Column(Integer)
    tblPost_CreatedUTC = Column(DateTime)
    tblPost_Permalink = Column(Text)
    tblPost_Distinguished = Column(String(50))
    tblPost_Stickied = Column(Boolean)
    tblPost_Edited = Column(Boolean)
    tblPost_IsOriginalContent = Column(Boolean)
    tblPost_Gilded = Column(Integer)
    tblPost_IsSelf = Column(Boolean)
    tblPost_LinkFlairText = Column(String(255))
    tblPost_ImageDescription = Column(Text)  # AI-generated image description
    tblPost_ImageDescriptionSentiment = Column(Float)  # VADER sentiment score for image description
    author = relationship("User", back_populates="posts")
    subreddit = relationship("Subreddit", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

class Comment(Base):
    __tablename__ = 'tblComment'
    tblComment_CommentID = Column(String(50), primary_key=True)
    tblComment_PostID = Column(String(50), ForeignKey('tblPost.tblPost_PostID'))
    tblComment_AuthorID = Column(String(50), ForeignKey('tblUser.tblUser_UserID'), nullable=True)
    tblComment_ParentID = Column(String(50), ForeignKey('tblComment.tblComment_CommentID'), nullable=True)
    tblComment_Content = Column(Text)
    tblComment_ContentSentiment = Column(Float)  # VADER sentiment score for the comment content
    tblComment_Score = Column(Integer)
    tblComment_CreatedUTC = Column(DateTime)
    tblComment_Permalink = Column(Text)
    tblComment_Distinguished = Column(String(50))
    tblComment_Stickied = Column(Boolean)
    tblComment_Edited = Column(Boolean)
    tblComment_Gilded = Column(Integer)
    tblComment_Controversiality = Column(Integer)
    tblComment_Depth = Column(Integer)
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent = relationship("Comment", remote_side=[tblComment_CommentID], primaryjoin="Comment.tblComment_ParentID == Comment.tblComment_CommentID")

# Create tables
Base.metadata.create_all(engine)

# Set up Reddit API
reddit = praw.Reddit(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    password=os.getenv('PASSWORD'),
    username=os.getenv('REDDIT_USERNAME'),
    user_agent='script by /u/kgbCO'
)

SUBREDDITS = [
    'personalfinance', 'investing', 'FinancialIndependence', 'CryptoCurrency',
    'WallStreetBets', 'ValueInvesting', 'StockMarket', 'Economics',
    'FinancialPlanning', 'CreditCards', 'RealEstateInvesting', 'Frugal',
    'Robinhood', 'Fidelity', 'Vanguard', 'Banking', 'Betterment',
    'Wealthfront', 'TDAmeritrade', 'MerrillEdge', 'ETrade', 'CharlesSchwab',
    'jpmorgan', 'investingforbeginners', 'bogleheads', 'finance', 'FinanceNews'
]  # Add your list of subreddits here

def analyze_image_url(image_url):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please look at the attached image and provide a concise summary as if you are a social media analyst writing a report about it. DO NOT provide a detailed summary of the image, just highlight the key points and a brief sentiment analysis."},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ]
                }
            ],
            max_tokens=3500,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"An error occurred while processing with AI: {e}")
        return None

def get_image_url(submission):
    if hasattr(submission, 'preview') and 'images' in submission.preview:
        return submission.preview['images'][0]['source']['url']
    return None

def get_user(user):
    if user is None:
        return None
    user_obj = session.query(User).filter_by(tblUser_Username=user.name).first()
    if not user_obj:
        user_obj = User(
            tblUser_UserID=user.id,
            tblUser_Username=user.name,
            tblUser_CreatedUTC=datetime.fromtimestamp(user.created_utc, timezone.utc),
            tblUser_CommentKarma=user.comment_karma,
            tblUser_LinkKarma=user.link_karma,
            tblUser_IsGold=bool(user.is_gold),
            tblUser_IsMod=bool(user.is_mod)
        )
        session.add(user_obj)
        session.commit()
    return user_obj

def get_subreddit(subreddit):
    subreddit_obj = session.query(Subreddit).filter_by(tblSubreddit_Name=subreddit.display_name).first()
    if not subreddit_obj:
        subreddit_obj = Subreddit(
            tblSubreddit_SubredditID=subreddit.id,
            tblSubreddit_Name=subreddit.display_name,
            tblSubreddit_Title=subreddit.title,
            tblSubreddit_Description=subreddit.description,
            tblSubreddit_Subscribers=subreddit.subscribers,
            tblSubreddit_ActiveUsers=subreddit.accounts_active,
            tblSubreddit_CreatedUTC=datetime.fromtimestamp(subreddit.created_utc, timezone.utc),
            tblSubreddit_Over18=bool(subreddit.over18),
            tblSubreddit_PublicDescription=subreddit.public_description,
            tblSubreddit_Lang=subreddit.lang,
            tblSubreddit_IconImg=subreddit.icon_img,
            tblSubreddit_BannerImg=subreddit.banner_img,
            tblSubreddit_UserIsSubscriber=bool(subreddit.user_is_subscriber)
        )
        session.add(subreddit_obj)
        session.commit()
    return subreddit_obj

def get_post(submission):
    post_obj = session.query(Post).filter_by(tblPost_PostID=submission.id).first()
    if not post_obj:
        user_obj = get_user(submission.author)
        subreddit_obj = get_subreddit(submission.subreddit)
        image_url = get_image_url(submission)
        image_description = None
        image_description_sentiment = None
        if image_url:
            image_description = analyze_image_url(image_url)
            if image_description:
                image_description_sentiment = analyzer.polarity_scores(image_description)['compound']
        post_obj = Post(
            tblPost_PostID=submission.id,
            tblPost_Title=submission.title,
            tblPost_TitleSentiment=analyzer.polarity_scores(submission.title)['compound'],
            tblPost_AuthorID=user_obj.tblUser_UserID if user_obj else None,
            tblPost_SubredditID=subreddit_obj.tblSubreddit_SubredditID,
            tblPost_Content=submission.selftext,
            tblPost_ContentSentiment=analyzer.polarity_scores(submission.selftext)['compound'],
            tblPost_URL=submission.url,
            tblPost_ImageURL=image_url,
            tblPost_Score=submission.score,
            tblPost_UpvoteRatio=submission.upvote_ratio,
            tblPost_NumComments=submission.num_comments,
            tblPost_CreatedUTC=datetime.fromtimestamp(submission.created_utc, timezone.utc),
            tblPost_Permalink=submission.permalink,
            tblPost_Distinguished=submission.distinguished,
            tblPost_Stickied=bool(submission.stickied),
            tblPost_Edited=bool(submission.edited),
            tblPost_IsOriginalContent=bool(submission.is_original_content),
            tblPost_Gilded=submission.gilded,
            tblPost_IsSelf=bool(submission.is_self),
            tblPost_LinkFlairText=submission.link_flair_text,
            tblPost_ImageDescription=image_description,
            tblPost_ImageDescriptionSentiment=image_description_sentiment
        )
        session.add(post_obj)
        session.commit()
    else:
        post_obj.tblPost_Score = submission.score
        post_obj.tblPost_UpvoteRatio = submission.upvote_ratio
        post_obj.tblPost_NumComments = submission.num_comments
        post_obj.tblPost_Gilded = submission.gilded
        session.commit()
    return post_obj

def get_comment(comment, post_obj, depth=0):
    if comment.author is None:
        return None
    comment_obj = session.query(Comment).filter_by(tblComment_CommentID=comment.id).first()
    if not comment_obj:
        user_obj = get_user(comment.author)
        parent_obj = session.query(Comment).filter_by(tblComment_CommentID=comment.parent_id).first() if comment.parent_id else None
        comment_obj = Comment(
            tblComment_CommentID=comment.id,
            tblComment_PostID=post_obj.tblPost_PostID,
            tblComment_AuthorID=user_obj.tblUser_UserID if user_obj else None,
            tblComment_ParentID=parent_obj.tblComment_CommentID if parent_obj else None,
            tblComment_Content=comment.body,
            tblComment_ContentSentiment=analyzer.polarity_scores(comment.body)['compound'],
            tblComment_Score=comment.score,
            tblComment_CreatedUTC=datetime.fromtimestamp(comment.created_utc, timezone.utc),
            tblComment_Permalink=comment.permalink,
            tblComment_Distinguished=comment.distinguished,
            tblComment_Stickied=bool(comment.stickied),
            tblComment_Edited=bool(comment.edited),
            tblComment_Gilded=comment.gilded,
            tblComment_Controversiality=comment.controversiality,
            tblComment_Depth=depth
        )
        session.add(comment_obj)
        session.commit()
    else:
        comment_obj.tblComment_Score = comment.score
        comment_obj.tblComment_Gilded = comment.gilded
        comment_obj.tblComment_Controversiality = comment.controversiality
        session.commit()
    return comment_obj


def fetch_recent_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    for submission in subreddit.new(limit=10):
        post_obj = get_post(submission)
        submission.comments.replace_more(limit=None)
        for comment in submission.comments.list():
            get_comment(comment, post_obj, depth=comment.depth)

def main():
    while True:
        try:
            for subreddit_name in SUBREDDITS:
                print(f"Fetching data from subreddit: {subreddit_name}")
                fetch_recent_posts(subreddit_name)
                print("Sleeping for 5 seconds between subreddits")
                time.sleep(5)  # Add a small delay between requests to different subreddits
        except TooManyRequests as e:
            print(f"Rate limit exceeded: {e}. Sleeping for 1 minute.")
            time.sleep(60)
        except Exception as e:
            print(f"An error occurred: {e}")
        print("Completed one iteration, sleeping for 60 seconds")
        time.sleep(60)

if __name__ == "__main__":
    main()
    session.close()
