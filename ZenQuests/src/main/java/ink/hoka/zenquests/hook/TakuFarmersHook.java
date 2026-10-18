package ink.hoka.zenquests.hook;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.event.Event;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.Plugin;
import ink.hoka.zenquests.ZenQuests;
import ink.hoka.zenquests.model.ObjectiveType;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.function.Consumer;

/**
 * Интеграция с TakuFarmers API 1.0 — без жёсткой зависимости: события ищутся по имени класса,
 * методы вызываются рефлексией. Нет TakuFarmers или какого-то события — просто пропускаем.
 */
public final class TakuFarmersHook implements Listener {

    private static final String CROP = "ink.hoka.takufarmers.crops.event.CropHitEvent";
    private static final String API = "ink.hoka.takufarmers.api.event.";

    private final ZenQuests plugin;
    private ClassLoader loader;

    private TakuFarmersHook(ZenQuests plugin) { this.plugin = plugin; }

    public static void tryRegister(ZenQuests plugin) {
        Plugin tf = Bukkit.getPluginManager().getPlugin("TakuFarmers");
        if (tf == null || !tf.isEnabled()) return;
        TakuFarmersHook h = new TakuFarmersHook(plugin);
        h.loader = tf.getClass().getClassLoader();
        List<String> ok = new ArrayList<>(), missing = new ArrayList<>();

        h.on(CROP, h::crop, ok, missing);
        h.on(API + "CookCompleteEvent", h::cook, ok, missing);
        h.on(API + "MillCompleteEvent", h::mill, ok, missing);
        h.on(API + "FlourSackCraftEvent", e -> h.player(e, ObjectiveType.FLOUR_SACK, null, 1), ok, missing);
        h.on(API + "FarmVisitEvent", e -> h.player(e, ObjectiveType.FARM_VISIT, null, 1), ok, missing);
        h.on(API + "NpcInteractEvent", e -> h.player(e, ObjectiveType.NPC_TALK, str(call(e, "getNpcId")), 1), ok, missing);
        h.on(API + "NpcDialogEvent", e -> h.player(e, ObjectiveType.DIALOG, str(call(e, "getDialogId")), 1), ok, missing);
        h.on(API + "EconomyChangeEvent", h::economy, ok, missing);
        h.on(API + "BedActionEvent", h::bed, ok, missing);

        if (!ok.isEmpty()) plugin.getLogger().info("TakuFarmers найден — подключено событий: " + ok.size() + " " + ok);
        if (!missing.isEmpty()) plugin.getLogger().warning("TakuFarmers: нет событий " + missing
                + " — соответствующие квесты не будут засчитываться (обнови TakuFarmers до API 1.0+).");
    }

    /** Подписаться на событие по имени класса. Отменённые события не засчитываются. */
    private void on(String className, Consumer<Event> handler, List<String> ok, List<String> missing) {
        String shortName = className.substring(className.lastIndexOf('.') + 1);
        try {
            Class<?> raw = Class.forName(className, true, loader);
            if (!Event.class.isAssignableFrom(raw)) { missing.add(shortName); return; }
            @SuppressWarnings("unchecked") Class<? extends Event> cls = (Class<? extends Event>) raw;
            Bukkit.getPluginManager().registerEvent(cls, this, EventPriority.MONITOR, (l, e) -> {
                if (!cls.isInstance(e)) return;
                try { handler.accept(e); }
                catch (Throwable t) { plugin.getLogger().warning("TakuFarmers " + shortName + ": " + t); }
            }, plugin, true);
            ok.add(shortName);
        } catch (ClassNotFoundException | LinkageError ex) {
            missing.add(shortName);
        }
    }

    // ── обработчики ──

    private void crop(Event e) {
        String result = str(call(e, "getResult"));
        boolean harvest = "HARVEST".equals(result), brk = "BREAK".equals(result);
        if (!harvest && !brk) return;                       // не выросло, не тот инструмент и т.п.
        if (!(call(e, "getPlayer") instanceof Player p)) return;
        String crop = str(call(e, "getCropId"));
        int amount = num(call(e, "getAmount"));
        progress(p, ObjectiveType.CROP_HIT, crop, 1);
        if (amount > 0) progress(p, ObjectiveType.CROP_HARVEST, crop, amount);
        if (brk) progress(p, ObjectiveType.CROP_BREAK, crop, 1);
    }

    /** Слот выхода у столов TakuFarmers (скалка, жёрнов, кухня). */
    private static final int TABLE_OUT = 15;

    private void cook(Event e) {
        if (!(call(e, "getPlayer") instanceof Player p)) return;
        String station = str(call(e, "getStationId"));
        Object res = call(e, "getResult");
        ItemStack result = res instanceof ItemStack it ? it : null;
        int n = result == null ? 1 : Math.max(1, result.getAmount());
        // TakuFarmers 18.10+: столы (скалка, жёрнов, кухня) шлют CookCompleteEvent на КАЖДЫЙ клик по слоту выхода, ещё до
        // того как предмет забран (и даже если забрать не удалось). Поэтому считаем не события, а сколько предметов
        // реально ушло из слота: сравниваем содержимое на следующем тике.
        Inventory top = p.getOpenInventory().getTopInventory();
        ItemStack slot = top.getSize() > TABLE_OUT ? top.getItem(TABLE_OUT) : null;
        if (result != null && slot != null && slot.isSimilar(result) && slot.getAmount() == result.getAmount()) {
            int before = slot.getAmount();
            Bukkit.getScheduler().runTask(plugin, () -> {
                Inventory t2 = p.getOpenInventory().getTopInventory();
                ItemStack after = t2 == top ? t2.getItem(TABLE_OUT) : null;
                int left = after != null && after.isSimilar(result) ? after.getAmount() : 0;
                int taken = before - left;
                if (taken <= 0) return;
                cooked(p, station, result, itemName(result), taken);
            });
            return;
        }
        // станции готовки (CookManager/CookMenu): одно событие на одно блюдо
        cooked(p, station, result, itemName(res), n);
    }

    /** Разводка по столам: стол семян → SEEDS, жёрнов → MILL (+OBTAIN считает сам трекер), остальное → COOK/COOK_ITEM. */
    private void cooked(Player p, String station, ItemStack result, String item, int n) {
        if ("seed_table".equals(station)) { progress(p, ObjectiveType.SEEDS, item, n); return; }
        if ("millstone".equals(station)) { progress(p, ObjectiveType.MILL, item, n); return; }
        progress(p, ObjectiveType.COOK, station, n);
        progress(p, ObjectiveType.COOK_ITEM, item, n);
    }

    /** BedActionEvent (API 1.1): грядки — прополка, полив, колодец, удобрение, посадка, сбор. */
    private void bed(Event e) {
        if (!(call(e, "getPlayer") instanceof Player p)) return;
        String action = str(call(e, "getAction"));
        String crop = str(call(e, "getCropId"));
        if (action == null) return;
        ObjectiveType t = switch (action) {
            case "WEED" -> ObjectiveType.WEED; case "WATER" -> ObjectiveType.WATER; case "WATER_ALL" -> ObjectiveType.WELL;
            case "FERTILIZE" -> ObjectiveType.FERTILIZE; case "PLANT" -> ObjectiveType.BED_PLANT; case "HARVEST" -> ObjectiveType.BED_HARVEST;
            default -> null;
        };
        if (t != null) progress(p, t, crop, 1);
    }

    private void mill(Event e) {
        if (!(call(e, "getPlayer") instanceof Player p)) return;
        progress(p, ObjectiveType.MILL, itemName(call(e, "getResult")), Math.max(1, num(call(e, "getAmount"))));
    }

    private void economy(Event e) {
        String type = str(call(e, "getType"));
        ObjectiveType t = "DEPOSIT".equals(type) ? ObjectiveType.EARN : "WITHDRAW".equals(type) ? ObjectiveType.SPEND : null;
        if (t == null) return;                              // SET — это админская установка, не заработок
        Object id = call(e, "getPlayerId");
        String cur = str(call(e, "getCurrency"));
        int amount = num(call(e, "getAmount"));
        if (!(id instanceof UUID uuid) || amount <= 0) return;
        // может прийти не из главного потока (Vault) — переносим
        Runnable r = () -> {
            Player p = Bukkit.getPlayer(uuid);
            if (p != null) progress(p, t, cur, amount);
        };
        if (Bukkit.isPrimaryThread()) r.run(); else Bukkit.getScheduler().runTask(plugin, r);
    }

    private void player(Event e, ObjectiveType type, String target, int amount) {
        if (call(e, "getPlayer") instanceof Player p) progress(p, type, target, amount);
    }

    private void progress(Player p, ObjectiveType t, String target, int amount) {
        if (amount > 0) plugin.quests().progress(p, t, target, amount);
    }

    // ── рефлексия ──

    private static Object call(Object o, String method) {
        try { return o.getClass().getMethod(method).invoke(o); }
        catch (Throwable t) { return null; }
    }

    private static String str(Object o) { return o == null ? null : o.toString(); }

    private static int num(Object o) {
        if (o instanceof Number n) return (int) Math.min(Integer.MAX_VALUE, Math.round(n.doubleValue()));
        return 0;
    }

    /** Имя предмета для целей: ванильный материал (BREAD) или id предмета Nexo, если он есть. */
    private static String itemName(Object o) {
        if (o instanceof ItemStack it) {
            String nexo = nexoId(it);
            return nexo != null ? nexo : it.getType().name();
        }
        if (o instanceof Material m) return m.name();
        return o == null ? null : o.toString().toUpperCase(Locale.ROOT);
    }

    private static String nexoId(ItemStack it) {
        try {
            Class<?> items = Class.forName("com.nexomc.nexo.api.NexoItems");
            Object id = items.getMethod("idFromItem", ItemStack.class).invoke(null, it);
            return id == null ? null : id.toString();
        } catch (Throwable t) { return null; }
    }
}
