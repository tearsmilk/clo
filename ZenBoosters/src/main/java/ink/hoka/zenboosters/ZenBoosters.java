package ink.hoka.zenboosters;

import ink.hoka.noratrum.Module;
import ink.hoka.noratrum.Noratrum;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

import java.util.List;

/**
 * Бустеры: временные множители — личные (игроку) и глобальные (всему серверу).
 * Типы (boosters.types в config.yml): coins (монеты с продажи рыбы и урожая), farm_xp (опыт фермы), fishing (клёв),
 * crop_growth (скорость роста растений), station_speed (скорость станций фермы).
 * Рыбалка и монеты за рыбу применяются здесь же (ZenFishing спрашивает {@link BoostersAPI}); урожай, опыт фермы, рост и станции —
 * на стороне TakuFarmers через тот же {@link BoostersAPI#multiplier(java.util.UUID, String)}.
 */
public final class ZenBoosters extends Module {

    private BoosterManager manager;
    private BoosterItems items;

    public ZenBoosters(Noratrum host) { super(host, "ZenBoosters", "boosters"); }

    @Override
    public void onEnable() {
        saveDefaultConfig();
        manager = new BoosterManager(this);
        manager.load();
        BoostersAPI.bind(manager);
        getServer().getPluginManager().registerEvents(manager, this);
        items = new BoosterItems(this);
        getServer().getPluginManager().registerEvents(items, this);
        BoosterCommand cmd = new BoosterCommand(this);
        registerCommand("booster", List.of("бустер", "бустеры", "boosters", "zenboosters"), cmd, cmd);
        Bukkit.getScheduler().runTaskTimer(this, manager::tick, 20L, 20L);
        ink.hoka.zenboosters.PapiHook.tryRegister(this);
        getLogger().info("Типов бустеров: " + manager.types().size());
    }

    @Override
    public void onDisable() { if (manager != null) manager.save(); BoostersAPI.bind(null); }

    public void reloadAll() { reloadConfig(); manager.load(); }
    public BoosterManager manager() { return manager; }
    public BoosterItems items() { return items; }

    public void msg(CommandSender to, String key, Object... kv) {
        String s = getConfig().getString("messages." + key);
        if (s == null || s.isEmpty()) return;
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        String prefix = getConfig().getString("messages.prefix", "");
        for (String line : s.split("\n")) to.sendMessage(Text.parse(prefix + line));
    }

    public void broadcast(String key, Object... kv) { for (Player p : Bukkit.getOnlinePlayers()) msg(p, key, kv); msg(Bukkit.getConsoleSender(), key, kv); }
}
