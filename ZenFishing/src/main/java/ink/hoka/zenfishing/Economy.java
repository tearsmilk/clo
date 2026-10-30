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

    /** Списать монеты (только Vault). @return false — нет Vault или не хватает. */
    public boolean take(Player p, double amount) {
        if (amount <= 0) return true;
        if (vault == null) return false;
        try {
            Object has = vault.getClass().getMethod("has", OfflinePlayer.class, double.class).invoke(vault, p, amount);
            if (!Boolean.TRUE.equals(has)) return false;
            Object r = vault.getClass().getMethod("withdrawPlayer", OfflinePlayer.class, double.class).invoke(vault, p, amount);
            return Boolean.TRUE.equals(r.getClass().getMethod("transactionSuccess").invoke(r));
        } catch (Throwable t) { plugin.getLogger().warning("Vault: " + t); return false; }
    }

    public boolean canCharge() { return vault != null; }

    /** Баланс игрока (Vault); 0 без Vault. */
    public double balance(Player p) {
        if (vault == null) return 0;
        try { return ((Number) vault.getClass().getMethod("getBalance", OfflinePlayer.class).invoke(vault, p)).doubleValue(); }
        catch (Throwable t) { return 0; }
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
