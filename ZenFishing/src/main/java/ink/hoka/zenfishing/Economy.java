package ink.hoka.zenfishing;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.bukkit.plugin.RegisteredServiceProvider;

import java.util.Locale;

/** Выплата за рыбу: Vault (рефлексией, без зависимости) или команда консоли из config.yml. */
public final class Economy {

    private final ZenFishing plugin;
    private Object vault;   // net.milkbowl.vault.economy.Economy

    public Economy(ZenFishing plugin) { this.plugin = plugin; }

    public void hook() {
        vault = null;
        if (Bukkit.getPluginManager().getPlugin("Vault") == null) return;
        try {
            Class<?> eco = Class.forName("net.milkbowl.vault.economy.Economy");
            RegisteredServiceProvider<?> rsp = Bukkit.getServicesManager().getRegistration(eco);
            if (rsp != null) { vault = rsp.getProvider(); plugin.getLogger().info("Vault найден — продажа рыбы через экономику Vault."); }
        } catch (Throwable ignored) { }
    }

    public boolean available() {
        String m = plugin.getConfig().getString("sell.method", "auto").toLowerCase(Locale.ROOT);
        boolean cmd = !plugin.getConfig().getString("sell.command", "").isBlank();
        return switch (m) { case "vault" -> vault != null; case "command" -> cmd; default -> vault != null || cmd; };
    }

    /** @return true, если выплата прошла */
    public boolean pay(Player p, double amount) {
        if (amount <= 0) return false;
        String m = plugin.getConfig().getString("sell.method", "auto").toLowerCase(Locale.ROOT);
        boolean useVault = vault != null && !m.equals("command");
        if (useVault) {
            try {
                Object r = vault.getClass().getMethod("depositPlayer", OfflinePlayer.class, double.class).invoke(vault, p, amount);
                Object ok = r.getClass().getMethod("transactionSuccess").invoke(r);
                if (Boolean.TRUE.equals(ok)) return true;
            } catch (Throwable t) { plugin.getLogger().warning("Vault: " + t); }
            if (m.equals("vault")) return false;
        }
        String cmd = plugin.getConfig().getString("sell.command", "");
        if (cmd.isBlank()) return false;
        String amt = amount == Math.floor(amount) ? String.valueOf((long) amount) : String.format(Locale.ROOT, "%.2f", amount);
        return Bukkit.dispatchCommand(Bukkit.getConsoleSender(), cmd.replace("{player}", p.getName()).replace("{amount}", amt));
    }
}
