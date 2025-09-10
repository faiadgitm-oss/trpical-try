def seed_database(db, Category, Item):
    if Category.query.first():
        return  # already seeded
    categories = [
"New Ice Cream Flavors",
"Natural Ice Cream",
"Tropical Traditions",
"Milkshake",
"Thick Shake",
"Tropical House Blends",
"Juice Bottles - 500 ML",
"Juices",
"Smoothie",
"Detox Healthy Juice",
"Lassi Drink (Laban)",
"Desi Kulfi",
"Refreshing Summers Drinks",
"Juice Bottles - 1.5 Liter",
"Popsicles",
"Tropical Mega Box"
    ]
    sample_items = []
    for c in categories:
        cat = Category(name=c)
        db.session.add(cat)
        db.session.flush()
        # create two example items per category
        for i in (1,2):
            itm = Item(
                name=f"{c} Item {i}",
                description=f"Delicious {c.lower()} item {i}.",
                price=round(50 + i * 20.5, 2),
                photo=None,
                out_of_stock=False,
                category_id=cat.id,
                variations={
                    "sizes": [{"name":"small","price_diff":0},{"name":"large","price_diff":25}],
                    "toppings": ["chocolate","nuts","sprinkles"]
                }
            )
            db.session.add(itm)
    db.session.commit()
    print("Seeded database with categories and items.")
