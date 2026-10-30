package ink.hoka.zenboosters;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.serializer.legacy.LegacyComponentSerializer;

/** &-коды и MiniMessage. */
final class Text {
    private Text() {}
    static Component parse(String s) {
        if (s == null) return Component.empty();
        if (s.contains("&") || s.contains("§")) return LegacyComponentSerializer.legacyAmpersand().deserialize(s.replace('§', '&'));
        return MiniMessage.miniMessage().deserialize(s);
    }
}
