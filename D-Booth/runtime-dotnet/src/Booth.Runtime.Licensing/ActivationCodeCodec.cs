using System.Text;

namespace Booth.Runtime.Licensing;

public static class ActivationCodeCodec
{
    private const string Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    public static string Encode(byte[] bytes)
    {
        var output = new StringBuilder();
        var buffer = 0;
        var bitsLeft = 0;

        foreach (var b in bytes)
        {
            buffer = (buffer << 8) | b;
            bitsLeft += 8;
            while (bitsLeft >= 5)
            {
                output.Append(Alphabet[(buffer >> (bitsLeft - 5)) & 31]);
                bitsLeft -= 5;
            }
        }

        if (bitsLeft > 0)
        {
            output.Append(Alphabet[(buffer << (5 - bitsLeft)) & 31]);
        }

        return string.Join("-", output.ToString().Chunk(5).Select(c => new string(c)));
    }

    public static byte[] Decode(string code)
    {
        var clean = new string(code.Where(char.IsLetterOrDigit).ToArray()).ToUpperInvariant();
        var bytes = new List<byte>();
        var buffer = 0;
        var bitsLeft = 0;

        foreach (var ch in clean)
        {
            var value = Alphabet.IndexOf(ch);
            if (value < 0)
            {
                throw new FormatException("Invalid activation code character.");
            }

            buffer = (buffer << 5) | value;
            bitsLeft += 5;
            if (bitsLeft >= 8)
            {
                bytes.Add((byte)((buffer >> (bitsLeft - 8)) & 255));
                bitsLeft -= 8;
            }
        }

        return bytes.ToArray();
    }
}

