import instaloader

#Load Instagram from the package
ig = instaloader.Instaloader()

#Instagram UserID
userID = "financeflashcards"

#download data
ig.download_profile(userID, profile_pic=True)