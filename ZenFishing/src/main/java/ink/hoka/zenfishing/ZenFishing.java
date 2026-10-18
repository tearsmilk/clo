package ink.hoka.zenfishing;

import ink.hoka.zenfishing.menu.FishMenu;
import ink.hoka.zenfishing.util.Text;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.command.PluginCommand;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.File;

/** Рыбалка: редкая рыба (fish.yml), прокачка удочки, бонусы Ферма+ (подписка ZenQuests), меню /рыбалка, продажа улова. */
public final class ZenFishing extends JavaPlugin {

    private FishRegistry fish;
    private Rods rods;
    private FishItems items;
    private Economy economy;
    private StatsStore stats;
    private FishMenu menu;
    private FishJournal journal;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!new File(getDataFolder(), "fish.yml").exists()) saveResource("fish.yml", false);
        fish = new FishRegistry(this); fish.load();
        rods = new Rods(this);
        items = new FishItems(this);
        economy = new Economy(this); economy.hook();
        stats = new StatsStore(this);
        menu = new FishMenu(this);
        getServer().getPluginManager().registerEvents(new FishingListener(this), this);
        getServer().getPluginManager().registerEvents(menu, this);
        journal = new FishJournal(this);
        getServer().getPluginManager().registerEvents(journal, this);
        ink.hoka.zenfishing.hook.PapiHook.tryRegister(this);
        PluginCommand cmd = getCommand("fishing");
        if (cmd != null) { FishCommand fc = new FishCommand(this); cmd.setExecutor(fc); cmd.setTabCompleter(fc); }
        Bukkit.getScheduler().runTaskTimer(this, () -> stats.saveDirty(), 20L * 60, 20L * 60);
        getLogger().info("Загружено рыбы: " + fish.size());
    }

    @Override
    public void onDisable() { if (stats != null) stats.saveDirty(); }

    public void reloadAll() { reloadConfig(); fish.load(); economy.hook(); }

    public FishRegistry fish() { return fish; }
    public Rods rods() { return rods; }
    public FishItems items() { return items; }
    public Economy economy() { return economy; }
    public StatsStore stats() { return stats; }
    public FishMenu menu() { return menu; }
    public FishJournal journal() { return journal; }
    public boolean quests() { return Bukkit.getPluginManager().getPlugin("ZenQuests") != null; }

    /** Ферма+: право premium.permission или подписка, выданная в ZenQuests (/квесты premium give). */
    public boolean isPremium(Player p) {
        if (p.hasPermission(getConfig().getString("premium.permission", "zenquests.premium"))) return true;
        try {
            Class<?> api = Class.forName("ink.hoka.zenquests.QuestsAPI");
            return Boolean.TRUE.equals(api.getMethod("isPremium", Player.class).invoke(null, p));
        } catch (Throwable t) { return false; }
    }

    public String premiumName() { return getConfig().getString("premium.name", "&6Ферма+"); }
    public String currency() { return getConfig().getString("sell.currency", ""); }

    /** Результат продажи. */
    public record Sale(int count, double amount) {}

    /** Оценка: сколько рыбы в инвентаре и на какую сумму (с бонусами удочки в руке и подписки). */
    public Sale appraise(Player p) {
        Rods.Bonus b = rods.bonus(p.getInventory().getItemInMainHand(), isPremium(p));
        int n = 0; double sum = 0;
        for (ItemStack it : p.getInventory().getStorageContents()) {
            FishItems.Caught c = items.read(it);
            if (c == null) continue;
            n += it.getAmount();
            sum += c.fish().priceFor(c.weight()) * (1 + b.sell()) * it.getAmount();
        }
        return new Sale(n, Math.round(sum * 100.0) / 100.0);
    }

    /** Продать всю рыбу из инвентаря. @return null — продавать нечего или нет экономики (сообщение уже отправлено). */
    public Sale sellAll(Player p) {
        Sale s = appraise(p);
        if (s.count() == 0) { msg(p, "nothing-to-sell"); return null; }
        if (!economy.available() || !economy.pay(p, s.amount())) { msg(p, "sell-unavailable"); return null; }
        ItemStack[] inv = p.getInventory().getStorageContents();
        for (int i = 0; i < inv.length; i++) if (items.read(inv[i]) != null) inv[i] = null;
        p.getInventory().setStorageContents(inv);
        PlayerStats st = stats.get(p);
        st.earned += s.amount(); st.dirty = true;
        msg(p, "sold", "count", s.count(), "amount", Text.num(s.amount()), "currency", currency());
        return s;
    }

    public void msg(CommandSender to, String key, Object... kv) {
        String s = getConfig().getString("messages." + key);
        if (s == null || s.isEmpty()) return;
        s = s.replace("{premium}", premiumName()).replace("{currency}", currency());
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        String prefix = getConfig().getString("messages.prefix", "");
        for (String line : s.split("\n")) to.sendMessage(Text.parse(prefix + line));
    }
}
