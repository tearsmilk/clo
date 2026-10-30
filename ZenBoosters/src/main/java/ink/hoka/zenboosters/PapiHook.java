package ink.hoka.zenboosters;

import me.clip.placeholderapi.expansion.PlaceholderExpansion;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.jetbrains.annotations.NotNull;

import java.util.Locale;

/**
 * %zenboosters_<тип>% — итоговый множитель (1 — нет), %zenboosters_<тип>_active% — 1/0, %zenboosters_<тип>_left% — осталось,
 * %zenboosters_count% — сколько активных бустеров у игрока (личные + глобальные).
 */
public final class PapiHook extends PlaceholderExpansion {
    private final ZenBoosters plugin;
    private PapiHook(ZenBoosters plugin) { this.plugin = plugin; }

    public static void tryRegister(ZenBoosters plugin) {
        if (Bukkit.getPluginManager().getPlugin("PlaceholderAPI") == null) return;
        try { new PapiHook(plugin).register(); plugin.getLogger().info("PlaceholderAPI найден — плейсхолдеры %zenboosters_*%."); }
        catch (Throwable t) { plugin.getLogger().warning("PlaceholderAPI: " + t); }
    }

    @Override public @NotNull String getIdentifier() { return "zenboosters"; }
    @Override public @NotNull String getAuthor() { return "fame/ktnqqq"; }
    @Override public @NotNull String getVersion() { return plugin.getDescription().getVersion(); }
    @Override public boolean persist() { return true; }

    @Override
    public String onRequest(OfflinePlayer p, String params) {
        String s = params.toLowerCase(Locale.ROOT);
        java.util.UUID id = p == null ? null : p.getUniqueId();
        BoosterManager m = plugin.manager();
        if (s.equals("count")) return String.valueOf(m.global().size() + (id == null ? 0 : m.personal(id).size()));
        String type = s, what = "mult";
        for (String suf : new String[]{"_active", "_left"}) if (s.endsWith(suf)) { type = s.substring(0, s.length() - suf.length()); what = suf.substring(1); }
        if (m.type(type) == null) return null;
        double mult = m.multiplier(id, type);
        return switch (what) {
            case "active" -> mult > 1 ? "1" : "0";
            case "left" -> mult > 1 ? BoosterManager.time(m.left(id, type)) : "";
            default -> BoosterManager.fmt(mult);
        };
    }
}
