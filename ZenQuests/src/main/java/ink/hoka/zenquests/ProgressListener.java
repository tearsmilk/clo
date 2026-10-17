package ink.hoka.zenquests;

import ink.hoka.zenquests.model.ObjectiveType;
import org.bukkit.GameMode;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.entity.Item;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.enchantment.EnchantItemEvent;
import org.bukkit.event.entity.EntityBreedEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityTameEvent;
import org.bukkit.event.inventory.CraftItemEvent;
import org.bukkit.event.inventory.FurnaceExtractEvent;
import org.bukkit.event.player.PlayerFishEvent;
import org.bukkit.event.player.PlayerItemConsumeEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.ItemStack;

import java.util.HashSet;
import java.util.Set;

/** Ловит действия игроков и двигает прогресс квестов. MONITOR — учитываем только то, что реально произошло. */
public final class ProgressListener implements Listener {

    private final ZenQuests plugin;
    // «возраст» у этих растений — таймер роста вверх, а не спелость
    private static final Set<String> GROWS_UP = Set.of("SUGAR_CANE", "CACTUS", "BAMBOO", "KELP", "KELP_PLANT",
            "TWISTING_VINES", "WEEPING_VINES", "CAVE_VINES", "CHORUS_FLOWER", "FIRE", "FROSTED_ICE", "MANGROVE_PROPAGULE");
    private final Set<String> placed = new HashSet<>();   // блоки, поставленные игроками (до рестарта)

    public ProgressListener(ZenQuests plugin) { this.plugin = plugin; }

    private QuestManager qm() { return plugin.quests(); }

    private static String key(Block b) {
        return b.getWorld().getName() + ":" + b.getX() + ":" + b.getY() + ":" + b.getZ();
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) { qm().refresh(e.getPlayer(), true); }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) { qm().unload(e.getPlayer()); }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlace(BlockPlaceEvent e) {
        if (plugin.getConfig().getBoolean("ignore-player-placed-blocks", true)) {
            if (placed.size() > 200_000) placed.clear();   // чтобы память не росла бесконечно
            placed.add(key(e.getBlockPlaced()));
        }
        if (e.getPlayer().getGameMode() == GameMode.CREATIVE) return;
        qm().progress(e.getPlayer(), ObjectiveType.PLACE, e.getBlockPlaced().getType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBreak(BlockBreakEvent e) {
        Block b = e.getBlock();
        boolean wasPlaced = placed.remove(key(b));
        if (e.getPlayer().getGameMode() == GameMode.CREATIVE) return;
        // культуры (пшеница, морковь, незерский нарост…): засчитываем только созревшие,
        // даже если посадил сам игрок — иначе фермерские квесты не выполнить
        if (b.getBlockData() instanceof org.bukkit.block.data.Ageable age && !GROWS_UP.contains(b.getType().name())) {
            if (age.getAge() < age.getMaximumAge()) return;
        } else if (wasPlaced && plugin.getConfig().getBoolean("ignore-player-placed-blocks", true)) return;
        qm().progress(e.getPlayer(), ObjectiveType.BREAK, b.getType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onKill(EntityDeathEvent e) {
        Player killer = e.getEntity().getKiller();
        if (killer == null) return;
        qm().progress(killer, ObjectiveType.KILL, e.getEntityType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onFish(PlayerFishEvent e) {
        if (e.getState() != PlayerFishEvent.State.CAUGHT_FISH) return;
        if (!(e.getCaught() instanceof Item item)) return;
        ItemStack s = item.getItemStack();
        qm().progress(e.getPlayer(), ObjectiveType.FISH, s.getType().name(), s.getAmount());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onCraft(CraftItemEvent e) {
        if (!(e.getWhoClicked() instanceof Player p)) return;
        ItemStack result = e.getRecipe().getResult();
        int crafts = 1;
        if (e.isShiftClick()) {
            // шифт-клик крафтит, пока хватает ингредиентов: берём минимальный стак в сетке
            int min = Integer.MAX_VALUE;
            for (ItemStack s : e.getInventory().getMatrix()) {
                if (s != null && s.getType() != Material.AIR) min = Math.min(min, s.getAmount());
            }
            crafts = min == Integer.MAX_VALUE ? 1 : min;
        }
        qm().progress(p, ObjectiveType.CRAFT, result.getType().name(), crafts * Math.max(1, result.getAmount()));
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onSmelt(FurnaceExtractEvent e) {
        qm().progress(e.getPlayer(), ObjectiveType.SMELT, e.getItemType().name(), e.getItemAmount());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onEat(PlayerItemConsumeEvent e) {
        qm().progress(e.getPlayer(), ObjectiveType.EAT, e.getItem().getType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onEnchant(EnchantItemEvent e) {
        qm().progress(e.getEnchanter(), ObjectiveType.ENCHANT, e.getItem().getType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBreed(EntityBreedEvent e) {
        if (e.getBreeder() instanceof Player p) qm().progress(p, ObjectiveType.BREED, e.getEntityType().name(), 1);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onTame(EntityTameEvent e) {
        if (e.getOwner() instanceof Player p) qm().progress(p, ObjectiveType.TAME, e.getEntityType().name(), 1);
    }

    /** Пешком: каждый новый блок по горизонтали = 1. Полёт, элитры и транспорт не считаются. */
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        if (e.getTo() == null) return;
        if (e.getFrom().getBlockX() == e.getTo().getBlockX() && e.getFrom().getBlockZ() == e.getTo().getBlockZ()) return;
        Player p = e.getPlayer();
        if (p.isFlying() || p.isGliding() || p.isInsideVehicle() || p.getGameMode() == GameMode.SPECTATOR) return;
        qm().progress(p, ObjectiveType.WALK, null, 1);
    }
}
