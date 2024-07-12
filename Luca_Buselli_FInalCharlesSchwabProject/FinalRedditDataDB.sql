CREATE DATABASE FinalRedditDataDB;
GO

USE FinalRedditDataDB;
GO

CREATE TABLE tblUser (
    tblUser_UserID VARCHAR(50) PRIMARY KEY,
    tblUser_Username VARCHAR(50) NOT NULL,
    tblUser_CreatedUTC DATETIME,
    tblUser_CommentKarma INT,
    tblUser_LinkKarma INT,
    tblUser_IsGold BIT,
    tblUser_IsMod BIT
);

CREATE TABLE tblSubreddit (
    tblSubreddit_SubredditID VARCHAR(50) PRIMARY KEY,
    tblSubreddit_Name VARCHAR(100) NOT NULL,
    tblSubreddit_Title VARCHAR(255),
    tblSubreddit_Description TEXT,
    tblSubreddit_Subscribers INT,
    tblSubreddit_ActiveUsers INT,
    tblSubreddit_CreatedUTC DATETIME,
    tblSubreddit_Over18 BIT,
    tblSubreddit_PublicDescription TEXT,
    tblSubreddit_Lang VARCHAR(10),
    tblSubreddit_IconImg TEXT,
    tblSubreddit_BannerImg TEXT,
    tblSubreddit_UserIsSubscriber BIT
);

CREATE TABLE tblPost (
    tblPost_PostID VARCHAR(50) PRIMARY KEY,
    tblPost_Title VARCHAR(300) NOT NULL,
    tblPost_TitleSentiment FLOAT,
    tblPost_AuthorID VARCHAR(50),
    tblPost_SubredditID VARCHAR(50),
    tblPost_Content TEXT,
    tblPost_ContentSentiment FLOAT,
    tblPost_URL TEXT,
    tblPost_ImageURL TEXT,
    tblPost_Score INT,
    tblPost_UpvoteRatio FLOAT,
    tblPost_NumComments INT,
    tblPost_CreatedUTC DATETIME,
    tblPost_Permalink TEXT,
    tblPost_Distinguished VARCHAR(50),
    tblPost_Stickied BIT,
    tblPost_Edited BIT,
    tblPost_IsOriginalContent BIT,
    tblPost_Gilded INT,
    tblPost_IsSelf BIT,
    tblPost_LinkFlairText VARCHAR(255),
    tblPost_ImageDescription TEXT,
    tblPost_ImageDescriptionSentiment FLOAT,
    FOREIGN KEY (tblPost_AuthorID) REFERENCES tblUser(tblUser_UserID),
    FOREIGN KEY (tblPost_SubredditID) REFERENCES tblSubreddit(tblSubreddit_SubredditID)
);

CREATE TABLE tblComment (
    tblComment_CommentID VARCHAR(50) PRIMARY KEY,
    tblComment_PostID VARCHAR(50),
    tblComment_AuthorID VARCHAR(50),
    tblComment_ParentID VARCHAR(50),
    tblComment_Content TEXT,
    tblComment_ContentSentiment FLOAT,
    tblComment_Score INT,
    tblComment_CreatedUTC DATETIME,
    tblComment_Permalink TEXT,
    tblComment_Distinguished VARCHAR(50),
    tblComment_Stickied BIT,
    tblComment_Edited BIT,
    tblComment_Gilded INT,
    tblComment_Controversiality INT,
    tblComment_Depth INT,
    FOREIGN KEY (tblComment_PostID) REFERENCES tblPost(tblPost_PostID),
    FOREIGN KEY (tblComment_AuthorID) REFERENCES tblUser(tblUser_UserID),
    FOREIGN KEY (tblComment_ParentID) REFERENCES tblComment(tblComment_CommentID)
);

