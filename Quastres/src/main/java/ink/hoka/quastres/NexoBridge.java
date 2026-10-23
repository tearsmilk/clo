package ink.hoka.quastres;

import org.bukkit.Bukkit;
import org.bukkit.inventory.ItemStack;

import java.lang.reflect.Method;

/** Nexo без жёсткой зависимости: NexoItems.idFromItem / itemFromId(...).build() через рефлексию. */
public final class NexoBridge {

    private Method idFromItem, itemFromId, build;

    public NexoBridge(Quastres plugin) {
        if (Bukkit.getPluginManager().getPlugin("Nexo") == null) return;
        try {
            Class<?> api = Class.forName("com.nexomc.nexo.api.NexoItems");
            idFromItem = api.getMethod("idFromItem", ItemStack.class);
            itemFromId = api.getMethod("itemFromId", String.class);
        } catch (Throwable t) {
            plugin.getLogger().warning("Nexo найден, но API недоступен: " + t);
            idFromItem = itemFromId = null;
        }
    }

    public boolean available() { return idFromItem != null; }

    public String id(ItemStack it) {
        if (idFromItem == null) return null;
        try { Object r = idFromItem.invoke(null, it); return r == null ? null : r.toString(); }
        catch (Throwable t) { return null; }
    }

    public ItemStack item(String id) {
        if (itemFromId == null) return null;
        try {
            Object builder = itemFromId.invoke(null, id);
            if (builder == null) return null;
            if (build == null) build = builder.getClass().getMethod("build");
            Object r = build.invoke(builder);
            return r instanceof ItemStack s ? s.clone() : null;
        } catch (Throwable t) { return null; }
    }
}
