package ink.hoka.zenquests.model;

/** Категория квестов. key — ключ в конфигах и в данных игрока. */
public enum Category {
    DAILY("daily"), WEEKLY("weekly"), SEASONAL("seasonal"), STORY("story");

    public final String key;

    Category(String key) { this.key = key; }

    public static Category byKey(String k) {
        for (Category c : values()) if (c.key.equalsIgnoreCase(k)) return c;
        return null;
    }
}
