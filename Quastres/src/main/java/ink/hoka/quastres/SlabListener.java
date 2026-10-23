package ink.hoka.quastres;

import org.bukkit.GameMode;
import org.bukkit.Material;
import org.bukkit.SoundGroup;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.block.BlockState;
import org.bukkit.block.data.BlockData;
import org.bukkit.block.data.type.Campfire;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockCookEvent;
import org.bukkit.event.block.BlockIgniteEvent;
import org.bukkit.event.block.BlockPhysicsEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.block.CampfireStartEvent;
import org.bukkit.event.entity.EntityChangeBlockEvent;
import org.bukkit.event.entity.ProjectileHitEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;

/** Установка/ломание полублоков и защита состояния костра. */
public final class SlabListener implements Listener {

    private final Quastres plugin;

    public SlabListener(Quastres plugin) { this.plugin = plugin; }

    private SlabRegistry reg() { return plugin.slabs(); }

    // ── установка по ПКМ ──

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onPlace(PlayerInteractEvent e) {
        if (e.getAction() != Action.RIGHT_CLICK_BLOCK || e.getClickedBlock() == null || e.getHand() == null) return;
        ItemStack it = e.getItem();
        SlabRegistry.Slab slab = reg().of(it);
        if (slab == null) return;
        e.setCancelled(true);
        if (e.getHand() != EquipmentSlot.HAND) return;
        Player p = e.getPlayer();
        Block clicked = e.getClickedBlock();
        Block target = clicked.isReplaceable() ? clicked : clicked.getRelative(e.getBlockFace());
        boolean water = target.getType() == Material.WATER;
        if (!target.isReplaceable() && !water) return;
        // игрок внутри будущего блока — не ставим (костёр ростом 7/16)
        org.bukkit.util.BoundingBox box = org.bukkit.util.BoundingBox.of(target.getLocation().toVector(), target.getLocation().toVector().add(new org.bukkit.util.Vector(1, 0.4375, 1)));
        for (var ent : target.getWorld().getNearbyEntities(box)) if (ent instanceof org.bukkit.entity.LivingEntity) return;
        BlockState before = target.getState();
        BlockData data = slab.data(water);
        target.setBlockData(data, true);
        BlockPlaceEvent place = new BlockPlaceEvent(target, before, clicked, it, p, true, EquipmentSlot.HAND);
        plugin.getServer().getPluginManager().callEvent(place);
        if (place.isCancelled() || !place.canBuild()) { before.update(true, false); plugin.msg(p, "cant-place"); return; }
        SoundGroup sg = reg().sounds(slab);
        p.getWorld().playSound(target.getLocation().add(0.5, 0.5, 0.5), sg.getPlaceSound(), sg.getVolume(), sg.getPitch());
        if (p.getGameMode() != GameMode.CREATIVE) it.setAmount(it.getAmount() - 1);
        p.swingMainHand();
    }

    // ── ломание: дроп — наш предмет ──

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBreak(BlockBreakEvent e) {
        SlabRegistry.Slab slab = reg().of(e.getBlock().getBlockData());
        if (slab == null) return;
        e.setDropItems(false);
        e.setExpToDrop(0);
        SoundGroup sg = reg().sounds(slab);
        e.getBlock().getWorld().playSound(e.getBlock().getLocation().add(0.5, 0.5, 0.5), sg.getBreakSound(), sg.getVolume(), sg.getPitch());
        if (e.getPlayer().getGameMode() == GameMode.CREATIVE) return;
        e.getBlock().getWorld().dropItemNaturally(e.getBlock().getLocation().add(0.5, 0.3, 0.5), reg().item(slab, 1));
    }

    // ── защита состояния (состояние = внешний вид) ──

    /** Огниво, огненный заряд, еда, лопата по нашему полублоку — ничего не делают. Лопата по обычному горящему костру — тоже (иначе он станет нашей плитой). */
    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onUse(PlayerInteractEvent e) {
        if (e.getAction() != Action.RIGHT_CLICK_BLOCK || e.getClickedBlock() == null) return;
        BlockData d = e.getClickedBlock().getBlockData();
        if (!(d instanceof Campfire c)) return;
        ItemStack it = e.getItem();
        if (reg().of(d) != null) { // наш полублок: любое «взаимодействие с костром» запрещаем, но дать поставить блок рядом
            if (it != null && (it.getType() == Material.FLINT_AND_STEEL || it.getType() == Material.FIRE_CHARGE || it.getType().isEdible() || it.getType().name().endsWith("_SHOVEL")))
                e.setCancelled(true);
            return;
        }
    }

    /** Обычный костёр ставим «на север» без сигнального флага: потушенный, он попадает в слот campfire/north (декоративный костёр),
     *  а не в случайную плиту. Для костра душ — то же (слот soul_campfire/north). */
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onVanillaPlace(BlockPlaceEvent e) {
        if (!plugin.getConfig().getBoolean("normalize-vanilla-campfire", true)) return;
        if (!(e.getBlockPlaced().getBlockData() instanceof Campfire c) || !c.isLit()) return;
        if (c.getFacing() == BlockFace.NORTH && !c.isSignalFire()) return;
        c.setFacing(BlockFace.NORTH); c.setSignalFire(false);
        e.getBlockPlaced().setBlockData(c, false);
    }

    @EventHandler(ignoreCancelled = true)
    public void onIgnite(BlockIgniteEvent e) { if (reg().of(e.getBlock().getBlockData()) != null) e.setCancelled(true); }

    @EventHandler
    public void onCook(CampfireStartEvent e) { if (reg().of(e.getBlock().getBlockData()) != null) e.setTotalCookTime(Integer.MAX_VALUE); }  // не отменяемое: готовка на нашем полублоке не завершится (еду туда и так не положить)

    @EventHandler(ignoreCancelled = true)
    public void onCookDone(BlockCookEvent e) { if (reg().of(e.getBlock().getBlockData()) != null) e.setCancelled(true); }

    /** Горящая стрела/огненный шар поджигают костёр — отменяем для наших. */
    @EventHandler(ignoreCancelled = true)
    public void onProjectile(ProjectileHitEvent e) {
        if (e.getHitBlock() != null && e.getEntity().getFireTicks() > 0 && reg().of(e.getHitBlock().getBlockData()) != null) e.setCancelled(true);
    }

    @EventHandler(ignoreCancelled = true)
    public void onEntityChange(EntityChangeBlockEvent e) { if (reg().of(e.getBlock().getBlockData()) != null) e.setCancelled(true); }

    /** Сено под костром включает signal_fire (физика блока) — для наших состояние не трогаем. */
    @EventHandler(ignoreCancelled = true)
    public void onPhysics(BlockPhysicsEvent e) {
        Material m = e.getBlock().getType();
        if ((m == Material.CAMPFIRE || m == Material.SOUL_CAMPFIRE) && reg().of(e.getBlock().getBlockData()) != null) e.setCancelled(true);
    }
}
