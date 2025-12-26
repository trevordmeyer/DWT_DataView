import pywt 
import numpy as np


test_coeffs1 = [2580.5703125,2580.5703125,2580.5703125,2580.5703125,5161.140625,2580.5703125,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
test_coeffs2 = [2367.20556640625,2367.20556640625,2367.20556640625,2367.20556640625,2367.20556640625,0.0,0.0,2367.20556640625,0.0,0.0,0.0,155134816.7944336,0.0,0.0,2367.20556640625,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,155134816.7944336,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,155134816.7944336,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,155134816.7944336,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
# test_coeffs1 = np.array([
# 2580.6, 2580.6, 2580.6, 2580.6, 5161.1, 2580.6,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0,
# 0, 0, 0, 0, 0, 0
# ])


# test_coeffs2 = np.zeros(120)
# test_coeffs2[[0,1,2,3,4,7,14]] = 2367.20616914404
# test_coeffs2[[11,29,41,56]] = -2367.20616914404

def test_waverec_api():
    # i expect test_coeffs1 to reconstruct to 81:160
    # i expect test_coeff2 to reconstruct to 1:80

    coeffs1, coeffs2 = [], []

    # first test what wavedec wants!!
    start = 0
    bk = [8, 8, 9, 11, 16, 25, 43]  # All except last = coeff array sizes
    for size in bk:
        coeffs1.append((np.array(test_coeffs1[start:start+size])))
        coeffs2.append((np.array(test_coeffs2[start:start+size])))
        start += size


    # print("Coefficients 1 for waverec:", coeffs1)
    # print("Coefficients 2 for waverec:", coeffs2)
    #print their final sizes:
    # for i, c in enumerate(coeffs1):
    #     print(f"Coeff 1 - Level {i} size: {c.shape}")
    # for i, c in enumerate(coeffs2):
    #     print(f"Coeff 2 - Level {i} size: {c.shape}")

# Suppose test_coeffs1 is your flat coefficient list (length should be 8+8+9+11+16+25+43 = 120)
    ##arr1 = np.arange(81, 161)
    #coeffs1 = pywt.wavedec(arr1, 'db4', mode='symmetric', level=4)
    #print("Coefficients 1 from wavedec:", coeffs1)
    
    # reconstruct and display waveform!
    rec1 = pywt.waverec(coeffs1, 'db4', mode = 'symmetric')
    print("Reconstructed Signal 1:", rec1)

    rec2 = pywt.waverec(coeffs2, 'db4', mode = 'symmetric')
    print("Reconstructed Signal 2:", rec2)


if __name__ == "__main__":
    # # print expected wavedec output
    # arr1 = np.arange(81, 161)
    # coeffs1 = pywt.wavedec(arr1, 'db4', mode='symmetric', level=6)
    # print("Coefficients 1 from wavedec:", coeffs1)
    test_waverec_api()