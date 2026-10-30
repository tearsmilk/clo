package ink.hoka.quastres;

import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.SoundGroup;
import org.bukkit.block.BlockFace;
import org.bukkit.block.data.BlockData;
import org.bukkit.block.data.type.Campfire;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;

import java.io.File;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/** blocks.yml → полублоки; ключ состояния «base|facing|signal» → полублок. */
public final class SlabRegistry {

    public record Slab(String id, String name, Material base, BlockFace facing, boolean signal, String sound) {
        public String stateKey() { return key(base, facing, signal); }
        public BlockData data(boolean waterlogged) {
            Campfire c = (Campfire) base.createBlockData();
            c.setFacing(facing); c.setLit(false); c.setSignalFire(signal); c.setWaterlogged(waterlogged);
            return c;
        }
    }

    static String key(Material base, BlockFace facing, boolean signal) { return base.name() + "|" + facing.name() + "|" + signal; }

    private final Quastres plugin;
    private final Map<String, Slab> byId = new LinkedHashMap<>();
    private final Map<String, Slab> byState = new HashMap<>();
    private final NamespacedKey kItem;

    public SlabRegistry(Quastres plugin) { this.plugin = plugin; kItem = new NamespacedKey(plugin, "slab"); }

    public void load() {
        byId.clear(); byState.clear();
        File f = new File(plugin.getDataFolder(), "blocks.yml");
        ConfigurationSection root = YamlConfiguration.loadConfiguration(f).getConfigurationSection("slabs");
        if (root == null) return;
        for (String id : root.getKeys(false)) {
            ConfigurationSection s = root.getConfigurationSection(id);
            if (s == null) continue;
            Material base = Material.matchMaterial(s.getString("base", "campfire").toUpperCase(Locale.ROOT));
            BlockFace facing;
            try { facing = BlockFace.valueOf(s.getString("facing", "north").toUpperCase(Locale.ROOT)); } catch (IllegalArgumentException e) { facing = null; }
            if ((base != Material.CAMPFIRE && base != Material.SOUL_CAMPFIRE) || facing == null || facing.getModY() != 0 || !facing.isCartesian()) {
                plugin.getLogger().warning("blocks.yml: " + id + " — base должен быть campfire/soul_campfire, facing — north/south/west/east; пропущен");
                continue;
            }
            Slab slab = new Slab(id, s.getString("name", id), base, facing, s.getBoolean("signal", false), s.getString("sound", "wood"));
            if (byState.containsKey(slab.stateKey())) {
                plugin.getLogger().warning("blocks.yml: " + id + " занимает то же состояние, что и " + byState.get(slab.stateKey()).id() + "; пропущен");
                continue;
            }
            byId.put(id, slab); byState.put(slab.stateKey(), slab);
        }
    }

    public Map<String, Slab> all() { return Collections.unmodifiableMap(byId); }
    public Slab get(String id) { return byId.get(id); }

    /** Полублок по состоянию блока (потушенный костёр нужной стороны/флага), иначе null. */
    public Slab of(BlockData d) {
        if (!(d instanceof Campfire c) || c.isLit()) return null;
        return byState.get(key(d.getMaterial(), c.getFacing(), c.isSignalFire()));
    }

    /** Предмет полублока: из Nexo (id = id полублока), иначе свой (бумага с item_model quastres:<id>). */
    public ItemStack item(Slab s, int amount) {
        ItemStack it = plugin.nexo().item(s.id());
        if (it == null) {
            it = new ItemStack(Material.PAPER);
            ItemMeta m = it.getItemMeta();
            m.displayName(Quastres.text(s.name()));
            m.addItemFlags(ItemFlag.values());
            try { m.setItemModel(new NamespacedKey("quastres", s.id())); } catch (Throwable ignored) { }
            it.setItemMeta(m);
        }
        ItemMeta m = it.getItemMeta();
        m.getPersistentDataContainer().set(kItem, PersistentDataType.STRING, s.id());
        it.setItemMeta(m);
        it.setAmount(Math.max(1, amount));
        return it;
    }

    /** Полублок по предмету: сначала Nexo-id, затем PDC. */
    public Slab of(ItemStack it) {
        if (it == null || it.getType().isAir()) return null;
        String nid = plugin.nexo().id(it);
        if (nid != null && byId.containsKey(nid)) return byId.get(nid);
        if (!it.hasItemMeta()) return null;
        String pid = it.getItemMeta().getPersistentDataContainer().get(kItem, PersistentDataType.STRING);
        return pid == null ? null : byId.get(pid);
    }

    public SoundGroup sounds(Slab s) {
        Material m = switch (s.sound().toLowerCase(Locale.ROOT)) {
            case "stone" -> Material.STONE; case "grass" -> Material.GRASS_BLOCK; case "sand" -> Material.SAND;
            case "gravel" -> Material.GRAVEL; case "wool" -> Material.WHITE_WOOL; case "snow" -> Material.SNOW_BLOCK;
            default -> Material.OAK_PLANKS;
        };
        return m.createBlockData().getSoundGroup();
    }
}
