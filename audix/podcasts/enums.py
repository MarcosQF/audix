from enum import Enum


class PodcastCategory(str, Enum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    COMEDY = "comedy"
    EDUCATION = "education"
    HEALTH = "health"
    NEWS = "news"
    SCIENCE = "science"
    SOCIETY = "society"
    SPORTS = "sports"
    TRUE_CRIME = "true_crime"


