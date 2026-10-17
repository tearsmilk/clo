package ink.hoka.zengroups.util;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextDecoration;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.serializer.legacy.LegacyComponentSerializer;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Парсинг текста в Adventure-компоненты.
 *
 * Поддерживает:
 *   • MiniMessage: &lt;gradient:#ff0000:#00ff00&gt;текст&lt;/gradient&gt;, &lt;rainbow&gt;, &lt;#ff8800&gt;, &lt;bold&gt; и т.д.
 *   • HEX в старом стиле: &amp;#ff8800
 *   • Классические коды: &amp;a &amp;l &amp;c ... (для обратной совместимости)
 *
 * Внутри всё приводится к MiniMessage и парсится один раз.
 */
public final class Text {

    private static final MiniMessage MM = MiniMessage.miniMessage();
    private static final LegacyComponentSerializer LEGACY = LegacyComponentSerializer.legacyAmpersand();

    private static final Pattern HEX = Pattern.compile("[&§]#([0-9A-Fa-f]{6})");

    private Text() {}

    private static final Pattern GLYPH = Pattern.compile("\\{glyph:([A-Za-z0-9_.-]+)}");

    /** {glyph:имя} → символ глифа Nexo (рефлексией, без зависимости). Нет Nexo или глифа — убирается. */
    public static String glyphs(String s) {
        if (s == null || !s.contains("{glyph:")) return s == null ? "" : s;
        Matcher m = GLYPH.matcher(s);
        StringBuilder sb = new StringBuilder();
        while (m.find()) m.appendReplacement(sb, Matcher.quoteReplacement(glyphChar(m.group(1))));
        m.appendTail(sb);
        return sb.toString();
    }

    private static String glyphChar(String name) {
        try {
            Class<?> fonts = Class.forName("com.nexomc.nexo.api.NexoFonts");
            Object g = fonts.getMethod("glyphFromName", String.class).invoke(null, name);
            if (g == null) return "";
            for (String mn : new String[]{"character", "getCharacter", "unicode", "getUnicode"}) {
                try { Object v = g.getClass().getMethod(mn).invoke(g); if (v != null) return v.toString(); } catch (NoSuchMethodException ignored) { }
            }
            for (String mn : new String[]{"unicodes", "getUnicodes"}) {
                try { Object v = g.getClass().getMethod(mn).invoke(g); if (v instanceof java.util.List<?> l && !l.isEmpty()) return String.valueOf(l.get(0)); } catch (NoSuchMethodException ignored) { }
            }
        } catch (Throwable ignored) { }
        return "";
    }

    public static Component parse(String s) {
        if (s == null) s = "";
        s = glyphs(s);
        String mm = legacyToMiniMessage(s);
        try {
            return MM.deserialize(mm).decoration(TextDecoration.ITALIC, false);
        } catch (Throwable ex) {
            // Если в строке кривые теги — не падаем, парсим как старый формат.
            return LEGACY.deserialize(s).decoration(TextDecoration.ITALIC, false);
        }
    }

    /** Убрать цвета (&-коды, &#hex и MiniMessage-теги) — для «серых» строк. */
    public static String strip(String s) {
        if (s == null) return "";
        return s.replaceAll("[&§]#[0-9A-Fa-f]{6}", "").replaceAll("[&§][0-9A-Fa-fK-Ok-oRr]", "").replaceAll("<[^<>]+>", "");
    }

    public static List<Component> parse(List<String> lines) {
        List<Component> out = new ArrayList<>();
        if (lines != null) {
            for (String l : lines) out.add(parse(l));
        }
        return out;
    }

    /** Превращает &amp;-коды и &amp;#RRGGBB в MiniMessage-теги. Готовые MiniMessage-теги не трогаются. */
    private static String legacyToMiniMessage(String in) {
        if (in == null || in.isEmpty()) return "";

        // 1) HEX: &#RRGGBB -> <#RRGGBB>
        Matcher m = HEX.matcher(in);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            m.appendReplacement(sb, "<#" + m.group(1) + ">");
        }
        m.appendTail(sb);
        String s = sb.toString();

        // 2) Классические коды &x / §x
        StringBuilder out = new StringBuilder(s.length() + 16);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if ((c == '&' || c == '§') && i + 1 < s.length()) {
                char code = Character.toLowerCase(s.charAt(i + 1));
                String tag = tagFor(code);
                if (tag != null) {
                    out.append(tag);
                    i++; // пропускаем сам код
                    continue;
                }
            }
            out.append(c);
        }
        return out.toString();
    }

    private static String tagFor(char code) {
        return switch (code) {
            case '0' -> "<black>";
            case '1' -> "<dark_blue>";
            case '2' -> "<dark_green>";
            case '3' -> "<dark_aqua>";
            case '4' -> "<dark_red>";
            case '5' -> "<dark_purple>";
            case '6' -> "<gold>";
            case '7' -> "<gray>";
            case '8' -> "<dark_gray>";
            case '9' -> "<blue>";
            case 'a' -> "<green>";
            case 'b' -> "<aqua>";
            case 'c' -> "<red>";
            case 'd' -> "<light_purple>";
            case 'e' -> "<yellow>";
            case 'f' -> "<white>";
            case 'l' -> "<bold>";
            case 'm' -> "<strikethrough>";
            case 'n' -> "<underlined>";
            case 'o' -> "<italic>";
            case 'k' -> "<obfuscated>";
            case 'r' -> "<reset>";
            default -> null;
        };
    }

    /** Оставшееся время: «3 д 4 ч», «5 ч 10 мин», «7 мин». */
    public static String duration(java.time.Duration d) {
        long m = Math.max(0, d.toMinutes());
        long days = m / 1440, hours = (m % 1440) / 60, mins = m % 60;
        if (days > 0) return days + " д " + hours + " ч";
        if (hours > 0) return hours + " ч " + mins + " мин";
        return mins + " мин";
    }

    /** Красивое число: целое без дробной части, иначе до 2 знаков без хвостовых нулей. */
    public static String num(double d) {
        if (Double.isNaN(d) || Double.isInfinite(d)) return "0";
        if (d == Math.floor(d) && Math.abs(d) < 1e15) {
            return String.valueOf((long) d);
        }
        return BigDecimal.valueOf(d)
                .setScale(2, RoundingMode.HALF_UP)
                .stripTrailingZeros()
                .toPlainString();
    }
}
