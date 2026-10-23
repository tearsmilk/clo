package ink.hoka.zenquests.model;

import org.bukkit.Material;

import java.util.List;
import java.util.regex.Pattern;

/**
 * Один квест из quests.yml.
 * targets — пусто = подходит что угодно; поддерживается * как шаблон: "*_LOG", "*_ORE".
 * rewardLines — что увидит игрок в меню; rewardCommands — что выполнит консоль ({player} — ник).
 * premium — квест только для подписки Ферма+.
 * premiumLines/premiumCommands — бонусная награда, которую подписчик получает сверху обычной.
 */
public record Quest(String id, Category category, String name, List<String> description, Material icon,
                    ObjectiveType type, List<String> targets, int amount,
                    List<String> rewardLines, List<String> rewardCommands,
                    boolean premium, List<String> premiumLines, List<String> premiumCommands) {

    public boolean matches(ObjectiveType t, String target) {
        if (t != type) return false;
        if (targets == null || targets.isEmpty()) return true;
        if (target == null) return false;
        String up = target.toUpperCase();
        for (String pat : targets) {
            String p = pat.toUpperCase();
            if (p.equals("ANY") || p.equals(up)) return true;
            if (p.contains("*")) {
                String regex = "\\Q" + p.replace("*", "\\E.*\\Q") + "\\E";
                if (Pattern.matches(regex, up)) return true;
            }
        }
        return false;
    }
}
