from feast import FeatureStore

store = FeatureStore(repo_path="/repo")

# User ID existant (1er de la table)
user_id = "0000-VHVEG"  
features = [
    "subs_profile_fv:months_active",
    "subs_profile_fv:monthly_fee",
    "subs_profile_fv:paperless_billing",
]

feature_dict = store.get_online_features(
    features=features,
    entity_rows=[{"user_id": user_id}],
).to_dict()

print("Online features for user:", user_id)
print(feature_dict)