package ink.hoka.zenfishing;

import ink.hoka.zenfishing.util.Text;
import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.Chunk;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Interaction;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractAtEntityEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.world.ChunkLoadEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Рыболовные сети. Предмет «Рыболовная сеть» (3D-модель net.model) ставится четырьмя ПКМ по блокам или воде: каждый клик —
 * угол, после четвёртого сеть натягивается на прямоугольник между углами по поверхности воды (ItemDisplay-плитки + Interaction).
 * Раз в net.check-seconds сеть с шансом ловит рыбу (только владелец, бонусы ночи и Ферма+). ПКМ по сети — забрать улов,
 * Shift+ПКМ — снять сеть. Сети хранятся в nets.yml и переживают рестарт.
 */
public final class Nets implements Listener {

    /** Поставленная сеть. */
    public static final class Net {
        public String id; public UUID owner; public String ownerName; public String world;
        public int minX, minZ, maxX, maxZ; public double y;
        public final List<String> caught = new ArrayList<>();
        public final List<UUID> entities = new ArrayList<>();
        public long placedAt;
        int tiles() { return (maxX - minX + 1) * (maxZ - minZ + 1); }
        boolean contains(int x, int z) { return x >= minX && x <= maxX && z >= minZ && z <= maxZ; }
        Location center(World w) { return new Location(w, (minX + maxX + 1) / 2.0, y, (minZ + maxZ + 1) / 2.0); }
    }

    private final ZenFishing plugin;
    private final NamespacedKey kItem, kNet;
    private final Map<String, Net> nets = new LinkedHashMap<>();
    private final Map<UUID, List<Location>> corners = new HashMap<>();
    private final File file;
    private boolean dirty;

    public Nets(ZenFishing plugin) {
        this.plugin = plugin;
        kItem = new NamespacedKey(plugin, "fishing_net");
        kNet = new NamespacedKey(plugin, "net_id");
        file = new File(plugin.getDataFolder(), "nets.yml");
        load();
        int period = Math.max(5, cfg().getInt("check-seconds", 60)) * 20;
        Bukkit.getScheduler().runTaskTimer(plugin, this::tick, period, period);
        Bukkit.getScheduler().runTaskTimer(plugin, this::ambient, 40L, 40L);
        Bukkit.getScheduler().runTaskLater(plugin, () -> { for (Net n : nets.values()) ensureSpawned(n); }, 40L);
    }

    private ConfigurationSection cfg() {
        ConfigurationSection c = plugin.getConfig().getConfigurationSection("net");
        return c != null ? c : plugin.getConfig().createSection("net");
    }

    public boolean enabled() { return cfg().getBoolean("enabled", true); }

    // ── предмет ──

    public ItemStack create() {
        ItemStack it = new ItemStack(Material.STRING);
        ItemMeta m = it.getItemMeta();
        m.displayName(Text.parse(cfg().getString("name", "&b🕸 Рыболовная сеть")));
        List<Component> lore = new ArrayList<>();
        for (String l : cfg().getStringList("lore")) lore.add(Text.parse(l));
        m.lore(lore);
        m.getPersistentDataContainer().set(kItem, PersistentDataType.BYTE, (byte) 1);
        m.addItemFlags(ItemFlag.values());
        String model = cfg().getString("model", "");
        if (model != null && !model.isBlank()) { try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { } }
        String tip = plugin.getConfig().getString("menu.tooltip-style", "");
        if (tip != null && !tip.isBlank()) { try { m.setTooltipStyle(NamespacedKey.fromString(tip)); } catch (Throwable ignored) { } }
        it.setItemMeta(m);
        return it;
    }

    public boolean isNet(ItemStack it) {
        return it != null && it.hasItemMeta() && it.getItemMeta().getPersistentDataContainer().has(kItem, PersistentDataType.BYTE);
    }

    public void give(Player p) {
        for (ItemStack rest : p.getInventory().addItem(create()).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
    }

    public int count(UUID owner) { int n = 0; for (Net x : nets.values()) if (x.owner.equals(owner)) n++; return n; }
    public int limit(Player p) { return cfg().getInt(plugin.isPremium(p) ? "max-per-player-premium" : "max-per-player", 3); }
    public Map<String, Net> all() { return nets; }

    // ── постановка: 4 ПКМ ──

    @EventHandler(priority = EventPriority.HIGH)
    public void onUse(PlayerInteractEvent e) {
        if (!enabled() || e.getHand() != EquipmentSlot.HAND) return;
        ItemStack it = e.getItem();
        if (!isNet(it)) return;
        if (e.getAction() != Action.RIGHT_CLICK_BLOCK && e.getAction() != Action.RIGHT_CLICK_AIR) return;
        e.setCancelled(true);
        Player p = e.getPlayer();
        if (p.isSneaking()) {
            if (corners.remove(p.getUniqueId()) != null) plugin.msg(p, "net-reset");
            return;
        }
        Block target = e.getClickedBlock();
        if (target == null || e.getAction() == Action.RIGHT_CLICK_AIR) {
            RayTraceResult r = p.rayTraceBlocks(6, FluidCollisionMode.ALWAYS);
            if (r == null || r.getHitBlock() == null) return;
            target = r.getHitBlock();
        }
        if (count(p.getUniqueId()) >= limit(p)) { plugin.msg(p, "net-limit", "max", limit(p)); return; }
        List<Location> list = corners.computeIfAbsent(p.getUniqueId(), k -> new ArrayList<>());
        Location loc = target.getLocation();
        if (!list.isEmpty()) {
            Location first = list.get(0);
            int span = cfg().getInt("max-size", 6);
            if (!first.getWorld().equals(loc.getWorld()) || Math.abs(first.getBlockX() - loc.getBlockX()) >= span || Math.abs(first.getBlockZ() - loc.getBlockZ()) >= span
                    || Math.abs(first.getBlockY() - loc.getBlockY()) > 3) {
                plugin.msg(p, "net-too-far", "max", span); return;
            }
            for (Location l : list) if (l.getBlockX() == loc.getBlockX() && l.getBlockZ() == loc.getBlockZ()) { plugin.msg(p, "net-same-corner"); return; }
        }
        list.add(loc);
        p.getWorld().spawnParticle(Particle.HAPPY_VILLAGER, loc.clone().add(0.5, 1.1, 0.5), 8, 0.2, 0.2, 0.2, 0);
        p.playSound(p.getLocation(), Sound.BLOCK_WOOL_PLACE, 0.8f, 1.3f + list.size() * 0.1f);
        if (list.size() < 4) { plugin.msg(p, "net-corner", "n", list.size()); return; }
        corners.remove(p.getUniqueId());
        place(p, list, it);
    }

    private void place(Player p, List<Location> c, ItemStack hand) {
        World w = c.get(0).getWorld();
        int minX = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE, yRef = 0;
        for (Location l : c) { minX = Math.min(minX, l.getBlockX()); maxX = Math.max(maxX, l.getBlockX()); minZ = Math.min(minZ, l.getBlockZ()); maxZ = Math.max(maxZ, l.getBlockZ()); yRef += l.getBlockY(); }
        yRef /= 4;
        int tiles = (maxX - minX + 1) * (maxZ - minZ + 1);
        if (tiles < cfg().getInt("min-tiles", 2)) { plugin.msg(p, "net-too-small"); return; }
        for (Net n : nets.values()) if (n.world.equals(w.getName()) && n.maxX >= minX && n.minX <= maxX && n.maxZ >= minZ && n.minZ <= maxZ && Math.abs(n.y - yRef) < 4) { plugin.msg(p, "net-overlap"); return; }
        // поверхность воды: по каждой клетке ищем воду с воздухом над ней около уровня кликов
        List<int[]> water = new ArrayList<>(); double surface = 0;
        for (int x = minX; x <= maxX; x++) for (int z = minZ; z <= maxZ; z++) {
            for (int y = yRef + 2; y >= yRef - 3; y--) {
                Block b = w.getBlockAt(x, y, z);
                if (b.getType() == Material.WATER && b.getRelative(0, 1, 0).getType().isAir()) { water.add(new int[]{x, y, z}); surface += y; break; }
            }
        }
        double need = cfg().getDouble("min-water", 0.5);
        if (water.isEmpty() || water.size() < Math.ceil(tiles * need)) { plugin.msg(p, "net-no-water"); return; }
        surface = Math.round(surface / water.size()) + 0.88;
        Net n = new Net();
        n.id = Long.toString(System.currentTimeMillis(), 36) + Integer.toString(ThreadLocalRandom.current().nextInt(1000), 36);
        n.owner = p.getUniqueId(); n.ownerName = p.getName(); n.world = w.getName();
        n.minX = minX; n.maxX = maxX; n.minZ = minZ; n.maxZ = maxZ; n.y = surface; n.placedAt = System.currentTimeMillis();
        nets.put(n.id, n); dirty = true;
        spawn(n, water);
        hand.setAmount(hand.getAmount() - 1);
        p.playSound(p.getLocation(), Sound.ENTITY_FISHING_BOBBER_SPLASH, 1f, 0.9f);
        w.spawnParticle(Particle.SPLASH, n.center(w), 40, (maxX - minX + 1) / 2.0, 0.1, (maxZ - minZ + 1) / 2.0, 0);
        plugin.msg(p, "net-placed", "w", maxX - minX + 1, "l", maxZ - minZ + 1);
        save();
    }

    // ── сущности ──

    private void spawn(Net n, List<int[]> water) {
        World w = Bukkit.getWorld(n.world);
        if (w == null) return;
        despawn(n);
        String model = cfg().getString("tile-model", "zenfishing:fishing_net_tile");
        ItemStack tile = new ItemStack(Material.STRING);
        ItemMeta m = tile.getItemMeta();
        try { m.setItemModel(NamespacedKey.fromString(model)); } catch (Throwable ignored) { }
        tile.setItemMeta(m);
        if (water == null) {
            water = new ArrayList<>();
            for (int x = n.minX; x <= n.maxX; x++) for (int z = n.minZ; z <= n.maxZ; z++) water.add(new int[]{x, (int) Math.floor(n.y), z});
        }
        for (int[] t : water) {
            Location l = new Location(w, t[0] + 0.5, n.y, t[2] + 0.5);
            ItemDisplay d = w.spawn(l, ItemDisplay.class, x -> {
                x.setItemStack(tile);
                x.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.FIXED);
                x.setTransformation(new Transformation(new Vector3f(0, 0, 0), new AxisAngle4f((float) Math.toRadians(90), 1, 0, 0), new Vector3f(1, 1, 1), new AxisAngle4f()));
                x.setBillboard(Display.Billboard.FIXED);
                x.setPersistent(true);
                x.setInvulnerable(true);
                x.getPersistentDataContainer().set(kNet, PersistentDataType.STRING, n.id);
            });
            n.entities.add(d.getUniqueId());
        }
        Location c = n.center(w).add(0, -0.35, 0);
        Interaction i = w.spawn(c, Interaction.class, x -> {
            x.setInteractionWidth(Math.max(n.maxX - n.minX, n.maxZ - n.minZ) + 1.0f);
            x.setInteractionHeight(0.7f);
            x.setResponsive(true);
            x.setPersistent(true);
            x.setInvulnerable(true);
            x.getPersistentDataContainer().set(kNet, PersistentDataType.STRING, n.id);
        });
        n.entities.add(i.getUniqueId());
        dirty = true;
    }

    private void despawn(Net n) {
        for (UUID u : n.entities) { Entity e = Bukkit.getEntity(u); if (e != null) e.remove(); }
        n.entities.clear();
        World w = Bukkit.getWorld(n.world);
        if (w == null) return;
        // подчистка «осиротевших» сущностей этой сети в загруженных чанках
        for (int cx = n.minX >> 4; cx <= n.maxX >> 4; cx++) for (int cz = n.minZ >> 4; cz <= n.maxZ >> 4; cz++) {
            if (!w.isChunkLoaded(cx, cz)) continue;
            for (Entity e : w.getChunkAt(cx, cz).getEntities())
                if (n.id.equals(e.getPersistentDataContainer().get(kNet, PersistentDataType.STRING))) e.remove();
        }
    }

    private boolean chunkLoaded(Net n) {
        World w = Bukkit.getWorld(n.world);
        return w != null && w.isChunkLoaded(n.minX >> 4, n.minZ >> 4) && w.isChunkLoaded(n.maxX >> 4, n.maxZ >> 4);
    }

    private void ensureSpawned(Net n) {
        if (!chunkLoaded(n)) return;
        boolean ok = !n.entities.isEmpty();
        for (UUID u : n.entities) if (Bukkit.getEntity(u) == null) { ok = false; break; }
        if (!ok) spawn(n, null);
    }

    @EventHandler
    public void onChunk(ChunkLoadEvent e) {
        Chunk c = e.getChunk();
        for (Net n : nets.values())
            if (n.world.equals(c.getWorld().getName()) && (n.minX >> 4) <= c.getX() && (n.maxX >> 4) >= c.getX() && (n.minZ >> 4) <= c.getZ() && (n.maxZ >> 4) >= c.getZ())
                Bukkit.getScheduler().runTask(plugin, () -> ensureSpawned(n));
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) { corners.remove(e.getPlayer().getUniqueId()); }

    // ── взаимодействие с сетью ──

    @EventHandler
    public void onClickAt(PlayerInteractAtEntityEvent e) { onClick(e); }

    private void onClick(PlayerInteractEntityEvent e) {
        if (e.getHand() != EquipmentSlot.HAND || !(e.getRightClicked() instanceof Interaction i)) return;
        String id = i.getPersistentDataContainer().get(kNet, PersistentDataType.STRING);
        if (id == null) return;
        e.setCancelled(true);
        Net n = nets.get(id);
        Player p = e.getPlayer();
        if (n == null) { i.remove(); return; }
        boolean admin = p.hasPermission("zenfishing.admin");
        if (!n.owner.equals(p.getUniqueId()) && !admin) { plugin.msg(p, "net-not-yours", "player", n.ownerName); return; }
        if (p.isSneaking()) { pickup(p, n); return; }
        collect(p, n);
    }

    private void collect(Player p, Net n) {
        if (n.caught.isEmpty()) { plugin.msg(p, "net-empty", "max", cfg().getInt("capacity", 8)); return; }
        int got = 0; PlayerStats st = plugin.stats().get(p);
        for (String id : new ArrayList<>(n.caught)) {
            Fish f = plugin.fish().get(id);
            if (f == null) continue;
            ItemStack it = plugin.items().create(f, 0, p);
            for (ItemStack rest : p.getInventory().addItem(it).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
            boolean first = st.record(f);
            if (first) plugin.msg(p, "new-species", "color", f.rarity().color(), "fish", f.name(), "known", st.known(), "total", plugin.fish().size());
            if (plugin.quests()) ink.hoka.zenfishing.hook.QuestsHook.progress(p, f, true, false, false);
            got++;
        }
        n.caught.clear(); dirty = true; save();
        p.playSound(p.getLocation(), Sound.ENTITY_ITEM_PICKUP, 1f, 0.9f);
        plugin.msg(p, "net-collected", "count", got);
    }

    private void pickup(Player p, Net n) {
        collect0(p, n);
        despawn(n);
        nets.remove(n.id); dirty = true; save();
        for (ItemStack rest : p.getInventory().addItem(create()).values()) p.getWorld().dropItemNaturally(p.getLocation(), rest);
        p.playSound(p.getLocation(), Sound.BLOCK_WOOL_BREAK, 1f, 1f);
        plugin.msg(p, "net-removed");
    }

    private void collect0(Player p, Net n) { if (!n.caught.isEmpty()) collect(p, n); }

    /** Снять все сети игрока (админ). @return сколько снято */
    public int removeAll(UUID owner) {
        int k = 0;
        for (Net n : new ArrayList<>(nets.values())) if (owner == null || n.owner.equals(owner)) { despawn(n); nets.remove(n.id); k++; }
        if (k > 0) { dirty = true; save(); }
        return k;
    }

    // ── ловля ──

    private void tick() {
        if (!enabled() || nets.isEmpty()) return;
        int cap = cfg().getInt("capacity", 8);
        double perTile = cfg().getDouble("chance-per-tile", 0.04), maxChance = cfg().getDouble("max-chance", 0.6);
        for (Net n : nets.values()) {
            if (n.caught.size() >= cap || !chunkLoaded(n)) continue;
            World w = Bukkit.getWorld(n.world);
            if (w == null) continue;
            long t = w.getTime(); boolean night = t >= 13000 && t < 23000;
            Player owner = Bukkit.getPlayer(n.owner);
            boolean premium = owner != null ? plugin.isPremium(owner) : plugin.getConfig().getBoolean("net.offline-premium", false);
            double chance = Math.min(maxChance, n.tiles() * perTile);
            if (night) chance *= cfg().getDouble("night-mult", 1.3);
            if (premium) chance *= cfg().getDouble("premium-mult", 1.25);
            if (ThreadLocalRandom.current().nextDouble() >= chance) continue;
            double luck = cfg().getDouble("luck", -0.2) + (night ? plugin.getConfig().getDouble("catch.night.luck", 0) : 0);
            Fish f = plugin.fish().roll(n.center(w), luck, premium);
            if (f == null) continue;
            n.caught.add(f.id()); dirty = true;
            w.spawnParticle(Particle.SPLASH, n.center(w), 15, 0.6, 0.1, 0.6, 0);
            if (owner != null && cfg().getBoolean("notify", true) && owner.getWorld().equals(w) && owner.getLocation().distanceSquared(n.center(w)) < 64 * 64)
                plugin.msg(owner, "net-caught", "color", f.rarity().color(), "fish", f.name(), "count", n.caught.size(), "max", cap);
        }
        if (dirty) save();
    }

    /** Пузырьки над сетью, в которой есть рыба. */
    private void ambient() {
        for (Net n : nets.values()) {
            if (n.caught.isEmpty() || !chunkLoaded(n)) continue;
            World w = Bukkit.getWorld(n.world);
            if (w == null) continue;
            Location c = n.center(w);
            w.spawnParticle(Particle.BUBBLE_POP, c.clone().add(ThreadLocalRandom.current().nextDouble(-1, 1), 0.1, ThreadLocalRandom.current().nextDouble(-1, 1)), 3, 0.3, 0.05, 0.3, 0);
        }
    }

    // ── хранение ──

    private void load() {
        nets.clear();
        if (!file.exists()) return;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(file);
        for (String id : y.getKeys(false)) {
            ConfigurationSection s = y.getConfigurationSection(id);
            if (s == null) continue;
            try {
                Net n = new Net();
                n.id = id; n.owner = UUID.fromString(s.getString("owner")); n.ownerName = s.getString("owner-name", "?"); n.world = s.getString("world");
                n.minX = s.getInt("min-x"); n.maxX = s.getInt("max-x"); n.minZ = s.getInt("min-z"); n.maxZ = s.getInt("max-z"); n.y = s.getDouble("y");
                n.placedAt = s.getLong("placed-at");
                n.caught.addAll(s.getStringList("caught"));
                for (String u : s.getStringList("entities")) n.entities.add(UUID.fromString(u));
                nets.put(id, n);
            } catch (Exception ex) { plugin.getLogger().warning("nets.yml: сеть " + id + " пропущена: " + ex); }
        }
    }

    public void save() {
        if (!dirty) return;
        YamlConfiguration y = new YamlConfiguration();
        for (Net n : nets.values()) {
            String k = n.id + ".";
            y.set(k + "owner", n.owner.toString()); y.set(k + "owner-name", n.ownerName); y.set(k + "world", n.world);
            y.set(k + "min-x", n.minX); y.set(k + "max-x", n.maxX); y.set(k + "min-z", n.minZ); y.set(k + "max-z", n.maxZ); y.set(k + "y", n.y);
            y.set(k + "placed-at", n.placedAt); y.set(k + "caught", n.caught);
            List<String> es = new ArrayList<>(); for (UUID u : n.entities) es.add(u.toString()); y.set(k + "entities", es);
        }
        try { y.save(file); dirty = false; }
        catch (IOException e) { plugin.getLogger().warning("Не сохранился nets.yml: " + e.getMessage()); }
    }

    public String describe(Net n) {
        return String.format(Locale.ROOT, "%s: %s %d,%d..%d,%d (%d кл.) рыбы %d", n.ownerName, n.world, n.minX, n.minZ, n.maxX, n.maxZ, n.tiles(), n.caught.size());
    }
}
