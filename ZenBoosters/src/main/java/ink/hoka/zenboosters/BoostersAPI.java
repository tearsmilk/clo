package ink.hoka.zenboosters;

import org.bukkit.entity.Player;

import java.util.UUID;

/**
 * API бустеров для других плагинов (TakuFarmers и т.п.), без зависимости от Noratrum в compile-time можно звать рефлексией:
 *   double m = ink.hoka.zenboosters.BoostersAPI.multiplier(playerUuid, "coins");
 * Типы: coins — монеты с продажи рыбы/урожая; farm_xp — опыт фермы; fishing — клёв; crop_growth — скорость роста растений
 * (делить время роста на m); station_speed — скорость станций/жёрнова/скалки/стола семян (делить время работы на m).
 * Возвращает 1.0, если бустеров нет или модуль выключен. Значение уже ограничено types.<id>.max.
 */
public final class BoostersAPI {
    private static BoosterManager manager;
    private BoostersAPI() {}
    static void bind(BoosterManager m) { manager = m; }

    public static boolean available() { return manager != null; }
    public static double multiplier(UUID player, String type) { return manager == null ? 1.0 : manager.multiplier(player, type); }
    public static double multiplier(Player player, String type) { return multiplier(player == null ? null : player.getUniqueId(), type); }
    /** Только глобальные бустеры (для серверных механик без игрока). */
    public static double global(String type) { return multiplier((UUID) null, type); }
    /** Сколько миллисекунд осталось у самого долгого активного бустера типа; 0 — нет. */
    public static long left(UUID player, String type) { return manager == null ? 0 : manager.left(player, type); }
    /** Выдать личный бустер (mult — множитель, millis — длительность). */
    public static void give(UUID player, String type, double mult, long millis, String by) { if (manager != null) manager.addPersonal(player, type, mult, millis, by); }
    public static void giveGlobal(String type, double mult, long millis, String by) { if (manager != null) manager.addGlobal(type, mult, millis, by); }
}
