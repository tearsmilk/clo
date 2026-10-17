package ink.hoka.zengroups.util;

import java.time.Duration;
import java.util.Locale;

/** Срок: 30d, 12h, 45m, 2w, 1d12h; просто число — дни; forever/навсегда/пусто — null (навсегда). */
public final class Terms {
    private Terms() {}

    public static Duration parse(String s) {
        if (s == null) return null;
        String in = s.trim().toLowerCase(Locale.ROOT);
        if (in.isEmpty() || in.equals("forever") || in.equals("навсегда") || in.equals("perm")) return null;
        Duration total = Duration.ZERO;
        StringBuilder num = new StringBuilder();
        for (char c : in.toCharArray()) {
            if (Character.isDigit(c)) { num.append(c); continue; }
            if (num.isEmpty()) throw new IllegalArgumentException(s);
            long n = Long.parseLong(num.toString());
            num.setLength(0);
            total = total.plus(switch (c) {
                case 'w', 'н' -> Duration.ofDays(7 * n);
                case 'd', 'д' -> Duration.ofDays(n);
                case 'h', 'ч' -> Duration.ofHours(n);
                case 'm', 'м' -> Duration.ofMinutes(n);
                default -> throw new IllegalArgumentException(s);
            });
        }
        if (!num.isEmpty()) total = total.plusDays(Long.parseLong(num.toString()));
        if (total.isZero() || total.isNegative()) throw new IllegalArgumentException(s);
        return total;
    }
}
