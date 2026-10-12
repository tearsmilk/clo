package ink.hoka.zenfishing;

import java.util.List;
import java.util.Set;

/**
 * Вид рыбы из fish.yml.
 * @param item    материал Minecraft или "nexo:<id>"
 * @param biomes  группы (OCEAN, RIVER…) или ключи биомов; пусто — везде
 */
public record Fish(String id, String name, String item, Rarity rarity, double minWeight, double maxWeight,
                   double price, double pricePerKg, boolean premium, Set<String> biomes, List<String> lore) {

    public double priceFor(double weight) { return price + pricePerKg * weight; }
}
