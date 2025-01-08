def category2dirname(category: str) -> str:
    """Converts a MediaWiki category title to a directory name."""
    return category.replace("Category:", "").replace("/", ":")
