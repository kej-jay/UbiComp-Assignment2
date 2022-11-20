using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Net.Http;
using TMPro;

public class Assignment3 : MonoBehaviour
{
    
    [SerializeField]
    private TextMeshPro myTextField;

    private static readonly HttpClient client = new HttpClient();
    private static string route = "http://169.254.140.200:3000";

    public static async void shareMarcel() {
        var values = new Dictionary<string, string>{};
        var content = new FormUrlEncodedContent(values);

        var response = await client.PostAsync(route + "/shareWithMarcel", content);
        var responseString = await response.Content.ReadAsStringAsync();
    }

    public async void getCurrentAction() {
        myTextField.text = "Loading";
        var responseString = await client.GetStringAsync(route + "/activity");
        Debug.Log(responseString);
        myTextField.text = responseString;
    }
}
