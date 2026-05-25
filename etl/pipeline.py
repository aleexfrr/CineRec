from transform import (
    transform_movies,
    transform_ratings,
    transform_users,
    save_processed_data
)

from extract import load_all_datasets

from load_mongodb import (
    insert_movies,
    insert_ratings,
    insert_users,
    create_indexes
)


def main():

    print("\n==============================")
    print(" MOVIELENS ETL PIPELINE ")
    print("==============================\n")

    # =========================
    # EXTRACT
    # =========================

    print("Loading raw datasets...")

    movies_df, ratings_df, users_df = load_all_datasets()

    print("Datasets loaded successfully.\n")

    # =========================
    # TRANSFORM
    # =========================

    print("Transforming movies dataset...")
    movies_clean = transform_movies(movies_df)

    print("Transforming ratings dataset...")
    ratings_clean = transform_ratings(ratings_df)

    print("Transforming users dataset...")
    users_clean = transform_users(users_df)

    print("Datasets transformed successfully.\n")

    # =========================
    # SAVE CLEAN DATASETS
    # =========================

    print("Saving processed datasets...")

    save_processed_data(
        movies_clean,
        ratings_clean,
        users_clean
    )

    print("Processed datasets saved.\n")

    # =========================
    # LOAD TO MONGODB
    # =========================

    print("Loading data into MongoDB...")

    insert_movies(movies_clean)

    insert_ratings(ratings_clean)

    insert_users(users_clean)

    create_indexes()

    print("\nMongoDB load completed.\n")

    print("==============================")
    print(" ETL PIPELINE FINISHED ")
    print("==============================\n")


if __name__ == "__main__":
    main()