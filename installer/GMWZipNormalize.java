import java.io.*;
import java.util.*;
import java.util.zip.*;

/** Deterministic stored ZIP normalizer, using only the installed game's JRE. */
public final class GMWZipNormalize {
    private static void word(OutputStream out, int value) throws IOException {
        out.write(value & 255); out.write((value >>> 8) & 255);
    }
    private static void dword(OutputStream out, long value) throws IOException {
        word(out, (int)value); word(out, (int)(value >>> 16));
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("input and output required");
        ZipFile input = new ZipFile(args[0]);
        TreeMap entries = new TreeMap();
        Enumeration list = input.entries();
        int total = 0;
        while (list.hasMoreElements()) {
            ZipEntry entry = (ZipEntry)list.nextElement();
            ByteArrayOutputStream data = new ByteArrayOutputStream();
            InputStream stream = input.getInputStream(entry);
            byte[] buffer = new byte[8192]; int count;
            while ((count = stream.read(buffer)) != -1) {
                data.write(buffer, 0, count); total += count;
                if (total > 16 * 1024 * 1024) throw new IOException("Archive too large");
            }
            stream.close();
            if (entries.put(entry.getName(), data.toByteArray()) != null) throw new IOException("Duplicate entry");
        }
        input.close();
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        ByteArrayOutputStream central = new ByteArrayOutputStream();
        Iterator it = entries.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry entry = (Map.Entry)it.next();
            byte[] name = ((String)entry.getKey()).getBytes("UTF-8");
            byte[] data = (byte[])entry.getValue();
            CRC32 crc = new CRC32(); crc.update(data);
            int offset = body.size();
            dword(body, 0x04034b50L); word(body, 20); word(body, 0); word(body, 0);
            word(body, 0); word(body, 33); dword(body, crc.getValue());
            dword(body, data.length); dword(body, data.length); word(body, name.length); word(body, 0);
            body.write(name); body.write(data);
            dword(central, 0x02014b50L); word(central, 20); word(central, 20); word(central, 0); word(central, 0);
            word(central, 0); word(central, 33); dword(central, crc.getValue());
            dword(central, data.length); dword(central, data.length); word(central, name.length);
            word(central, 0); word(central, 0); word(central, 0); word(central, 0); dword(central, 0); dword(central, offset);
            central.write(name);
        }
        FileOutputStream out = new FileOutputStream(args[1]);
        body.writeTo(out); central.writeTo(out);
        dword(out, 0x06054b50L); word(out, 0); word(out, 0);
        word(out, entries.size()); word(out, entries.size());
        dword(out, central.size()); dword(out, body.size()); word(out, 0);
        out.close();
    }
}
