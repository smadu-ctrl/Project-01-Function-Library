#What category gets the most interaction
#How quickly categories gain interactions
categories = [
    "Sports",
    "Internships and/or Job Advice",
    "Course Advice",
    "Campus Life",
    "Lost items",
    "Miscellaneous"
    ]

#simple
validate_post_data() #Post dict has all required keys and correct types
clean_text() #Standardizes text for analysis (categorizations, etc.)
is_valid_date() #Confirms user-input or dataset dates are formatted properly
format_datetime() #Converts timestamps to readable strings
calculate_engagement_score() #Combines upvotes/comments into single metric for sorting

#medium
categorize_post() #assigns each reddit post to category
analyze_post_trends() # Counts posts per category for trend tracking
get_top_posts() #Finds the top post by engagement score
filter_posts_by_date() #Selects posts within a specific time range
anazlyze_post_sentiment() #Uses text to measure sentiment (positive, negative, neutral)

#complex
aggregate_semester_data() #calculates total and average engagement per category for the semester
compare_trends_over_time() #measures how category frequencies change week to week
generate_summary_report() #Writes analysis results to a CSV report
visualize_trends() #creates a chart of category post trends
summarize_semester_findings() #Builds readable summary paragraph for reports/presentations