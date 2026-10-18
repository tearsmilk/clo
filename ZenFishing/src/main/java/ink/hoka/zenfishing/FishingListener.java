package ink.hoka.zenfishing;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.entity.FishHook;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerFishEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;

import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;

/** Клёв быстрее от уровня удочки/подписки; ванильная рыба заменяется на нашу; опыт удочке; статистика. */
public final class FishingListener implements Listener {

    private static final Set<Material> VANILLA_FISH = Set.of(Material.COD, Material.SALMON, Material.TROPICAL_FISH, Material.PUFFERFISH);
    private final ZenFishing plugin;

    public FishingListener(ZenFishing plugin) { this.plugin = plugin; }

    private ItemStack rod(Player p, PlayerFishEvent e) {
        EquipmentSlot hand;
        try { hand = e.getHand(); } catch (Throwable t) { hand = null; }
        if (hand == EquipmentSlot.OFF_HAND) return p.getInventory().getItemInOffHand();
        ItemStack main = p.getInventory().getItemInMainHand();
        return plugin.rods().isRod(main) ? main : p.getInventory().getItemInOffHand();
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onFish(PlayerFishEvent e) {
        Player p = e.getPlayer();
        if (e.getState() == PlayerFishEvent.State.FISHING) {
            Rods.Bonus b = plugin.rods().bonus(rod(p, e), plugin.isPremium(p));
            double bite = Math.min(0.9, b.bite() + (isNight(p) ? plugin.getConfig().getDouble("catch.night.bite-speed", 0) : 0));
            if (bite > 0) {
                FishHook h = e.getHook();
                try {
                    h.setMinWaitTime((int) Math.max(5, Math.round(100 * (1 - bite))));
                    h.setMaxWaitTime((int) Math.max(20, Math.round(600 * (1 - bite))));
                } catch (Throwable ignored) { }
            }
            return;
        }
        if (e.getState() != PlayerFishEvent.State.CAUGHT_FISH) return;
        if (!(e.getCaught() instanceof Item item)) return;
        if (!VANILLA_FISH.contains(item.getItemStack().getType())) return;   // хлам и сокровища — ванильные

        ItemStack rod = rod(p, e);
        boolean premium = plugin.isPremium(p);
        Rods.Bonus b = plugin.rods().bonus(rod, premium);
        Location where = e.getHook().getLocation();
        boolean night = isNight(p);
        double luck = b.luck() + (night ? plugin.getConfig().getDouble("catch.night.luck", 0) : 0);
        Fish f = plugin.fish().roll(where, luck, premium);
        if (f == null) return;
        double weight = plugin.fish().rollWeight(f, b.big());
        item.setItemStack(plugin.items().create(f, weight, p));
        handleCatch(p, f, weight, rod, b, false);
        if (night && plugin.getConfig().getBoolean("catch.night.message", true) && f.rarity().order() >= 2) plugin.msg(p, "night-bite");

        if (ThreadLocalRandom.current().nextDouble() < b.dbl()) {
            Fish f2 = plugin.fish().roll(where, luck, premium);
            if (f2 != null) {
                double w2 = plugin.fish().rollWeight(f2, b.big());
                ItemStack extra = plugin.items().create(f2, w2, p);
                for (ItemStack rest : p.getInventory().addItem(extra).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
                plugin.msg(p, "caught-double", "color", f2.rarity().color(), "fish", f2.name(), "weight", ink.hoka.zenfishing.util.Text.num(w2));
                handleCatch(p, f2, w2, rod, b, true);
            }
        }
    }

    /** Ночь в мире игрока: 13000..23000 тиков (от заката до рассвета). */
    static boolean isNight(Player p) {
        long t = p.getWorld().getTime();
        return t >= 13000 && t < 23000;
    }

    private void handleCatch(Player p, Fish f, double weight, ItemStack rod, Rods.Bonus b, boolean extra) {
        PlayerStats st = plugin.stats().get(p);
        boolean record = st.record(f, weight);
        int xp = (int) Math.round(f.rarity().xp() * b.xpMul());
        if (!extra) plugin.msg(p, "caught", "color", f.rarity().color(), "fish", f.name(), "weight", ink.hoka.zenfishing.util.Text.num(weight),
                "rarity", f.rarity().name(), "xp", xp);
        if (record && st.count.getOrDefault(f.id(), 0) > 1)
            plugin.msg(p, "record", "color", f.rarity().color(), "fish", f.name(), "weight", ink.hoka.zenfishing.util.Text.num(weight));
        Rarity from = plugin.fish().rarity(plugin.getConfig().getString("catch.announce-from", "epic").toLowerCase(Locale.ROOT));
        if (from != null && f.rarity().order() >= from.order())
            for (Player o : Bukkit.getOnlinePlayers()) if (o != p)
                plugin.msg(o, "announce", "player", p.getName(), "color", f.rarity().color(), "fish", f.name(),
                        "weight", ink.hoka.zenfishing.util.Text.num(weight), "rarity", f.rarity().name());
        if (plugin.getConfig().getBoolean("catch.sounds", true)) {
            if (f.rarity().order() >= 2) p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 0.8f, 1.4f);
            if (f.rarity().order() >= 4) p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1f, 1f);
        }
        if (plugin.rods().isRod(rod)) {
            int up = plugin.rods().addXp(p, rod, xp);
            if (up > 0) {
                if (up >= plugin.rods().maxLevel()) plugin.msg(p, "level-max"); else plugin.msg(p, "level-up", "level", up);
                if (plugin.getConfig().getBoolean("catch.sounds", true)) p.playSound(p.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 1f, 1.2f);
            }
        }
        if (plugin.quests()) ink.hoka.zenfishing.hook.QuestsHook.progress(p, f, extra, isNight(p), weight >= plugin.getConfig().getDouble("catch.big-kg", 10));
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) { plugin.stats().unload(e.getPlayer().getUniqueId()); }
}
