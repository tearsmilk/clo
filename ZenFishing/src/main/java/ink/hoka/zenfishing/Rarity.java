package ink.hoka.zenfishing;

/** Редкость рыбы из fish.yml (rarities). Порядок — по возрастанию редкости. */
public record Rarity(String id, String name, String color, double weight, int xp, int order) {}
